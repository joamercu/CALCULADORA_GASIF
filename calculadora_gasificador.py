# calculadora_gasificador.py  ⏤ Versión 2.0
# ---------------------------------------------------------------------------
# Calculadora detallada para gasificadores atmosféricos de GNL → GNG.
# ● Modela transferencia de calor por convección natural/forzada en bancos
#   de tubos aletados verticales.
# ● Permite combinar módulos en PAR / SERIE y estimar respuesta térmica.
# ● Basado en FYNLQ‑2000‑10Q y validaciones del chat.
# ---------------------------------------------------------------------------
from __future__ import annotations
from dataclasses import dataclass
from math import pi, sqrt

# -------------------- 1. Propiedades físicas simplificadas ------------------
RHO_LNG = 430         # kg/m³   (−160 °C)
CP_LNG  = 2.5e3       # J/kg·K  (líquido ≈ const.)

RHO_GNG = 1.0         # kg/m³   (0 °C, 1 bar)
CP_GNG  = 2.1e3       # J/kg·K  (gas)

LATENT  = 510e3       # J/kg    (∆h vaporización promedio GNL)

MU_AIR   = 1.8e-5     # Pa·s    (aire 0 – 30 °C)
K_AIR    = 0.026      # W/m·K   (aire)
PR_AIR   = 0.71       # —       (Prandtl)

# -------------------- 2. Clases de diseño -----------------------------------
@dataclass
class FinTubeGeometry:
    tube_od_mm: float = 28        # Ø exterior del liner (sin aletas)
    fin_height_mm: float = 200
    fins_per_tube: int = 12
    fin_efficiency: float = 0.85  # eficiencia de aleta (ε)

    @property
    def area_per_meter(self) -> float:
        """m² de superficie primaria+secundaria por metro de tubo"""
        A_primary = pi * (self.tube_od_mm/1000)  # circunferencia * 1 m
        A_fins = self.fins_per_tube * (2 * pi * (self.tube_od_mm/1000) *
                                        self.fin_height_mm/1000)
        return (A_primary + self.fin_efficiency * A_fins)


@dataclass
class AmbientConditions:
    T_air: float = 15             # °C ambiente
    v_wind: float = 0.5           # m/s  (0 = convección natural)

    def h_coefficient(self, D_h: float) -> float:
        """Coef. h [W/m²·K] por convección mixta sobre cilindro vertical"""
        beta = 1/273.15  # aprox β (1/T) en K⁻¹
        # Convección natural ⟶ Churchill & Chu para placa vertical infinita
        Gr = 9.81 * beta * (self.T_air + 273.15 - (-160 + 273.15)) * D_h**3 / MU_AIR**2
        Ra = Gr * PR_AIR
        Nu_nat = (0.825 + 0.387*Ra**(1/6) / (1 + (0.492/PR_AIR)**(9/16))**(8/27))**2
        # Convección forzada ⟶ Zukauskas para cilindro transversal
        Re = RHO_GNG * self.v_wind * D_h / MU_AIR
        C, m = (0.3, 0.62) if Re < 1e5 else (0.027, 0.805)
        Nu_for = C * Re**m * PR_AIR**0.37
        n = 3
        Nu_mix = (Nu_nat**n + Nu_for**n)**(1/n)
        return Nu_mix * K_AIR / D_h


@dataclass
class ModuleConfig:
    tubes_x: int
    tubes_y: int
    spacing_x_mm: float = 215
    spacing_y_mm: float = 300

    def footprint_mm(self, tube_d_mm: float) -> tuple[float, float]:
        fx = (self.tubes_x - 1)*self.spacing_x_mm + tube_d_mm
        fy = (self.tubes_y - 1)*self.spacing_y_mm + tube_d_mm
        return fx, fy

    @property
    def n_tubes(self):
        return self.tubes_x * self.tubes_y


@dataclass
class Gasifier:
    geom: FinTubeGeometry
    module: ModuleConfig
    tube_length_mm: float = 4600
    ambient: AmbientConditions = AmbientConditions()

    def capacity(self, mode="steady") -> float:
        """Devuelve capacidad Nm³/h para condiciones dadas.
            mode = "steady" (quasi‑estacionario) o "cold‑start" (respuesta).
        """
        D_h = (self.geom.tube_od_mm + 2*self.geom.fin_height_mm)/1000
        h = self.ambient.h_coefficient(D_h)
        U = h  # Resistencias internas ≪ externas, aluminio.
        A_per_tube = self.geom.area_per_meter * (self.tube_length_mm/1000)
        Qtot = U * A_per_tube * (self.ambient.T_air - (-160))  # W
        m_dot = Qtot / (LATENT + CP_LNG*((-160) - (-160)))      # kg/s
        nTubes = self.module.n_tubes
        flow_total = m_dot * nTubes * 3600 / 0.693  # kg→Nm³ (ρ≈0.693 kg/Nm³)
        if mode == "cold-start":
            tau_s = self.thermal_time_constant()  # h
            return flow_total * 0.5               # primera aproximación
        return flow_total

    def thermal_time_constant(self) -> float:
        mass_Al = 2700 * (self.geom.area_per_meter * 0.002) * (self.tube_length_mm/1000) * self.module.n_tubes
        Cth = mass_Al * 900      # J/K   (c_p aluminio)
        hA = self.ambient.h_coefficient((self.geom.tube_od_mm + 2*self.geom.fin_height_mm)/1000) * self.geom.area_per_meter * (self.tube_length_mm/1000) * self.module.n_tubes
        return Cth / hA / 3600   # horas

    def summary(self):
        fx, fy = self.module.footprint_mm(self.geom.tube_od_mm + 2*self.geom.fin_height_mm)
        return {
            "n_tubes": self.module.n_tubes,
            "area_total_m2": round(self.geom.area_per_meter*(self.tube_length_mm/1000)*self.module.n_tubes, 1),
            "capacity_Nm3_h": round(self.capacity()),
            "footprint_mm": {"x": round(fx), "y": round(fy), "z": self.tube_length_mm},
            "tau_h": round(self.thermal_time_constant(), 2)
        }

# -------------------- Ejemplo de uso ----------------------------------------
if __name__ == "__main__":
    geom = FinTubeGeometry(fin_height_mm=300, fins_per_tube=16)
    mod  = ModuleConfig(tubes_x=8, tubes_y=18, spacing_x_mm=215, spacing_y_mm=215)
    amb  = AmbientConditions(T_air=20, v_wind=1.0)  # viento ligero

    gasif = Gasifier(geom, mod, tube_length_mm=10600, ambient=amb)

    print("\n=== Gasificador 10.6 m, 144 tubos ===")
    for k, v in gasif.summary().items():
        print(f"{k}: {v}")

    # Conexión de 2 módulos en SERIE (flujo por un módulo y luego el otro)
    gasif_series = Gasifier(geom, mod, tube_length_mm=10600, ambient=amb)
    cap_series = gasif_series.capacity()  # igual que uno, restricción térmica

    # En PARALELO se duplica el caudal (flujo dividido)
    cap_parallel = cap_series * 2

    print(f"\nCapacidad SERIE    : {round(cap_series)} Nm³/h")
    print(f"Capacidad PARALELO : {round(cap_parallel)} Nm³/h")