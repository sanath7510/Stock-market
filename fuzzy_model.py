
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# ------------ Universes ------------
# Keep ranges consistent with your project
PM_UNI  = np.arange(-200, 201, 1)   # Profit Margin (%)
DR_UNI  = np.arange(0,   101, 1)    # Debt Ratio (%)
ROA_UNI = np.arange(-100, 101, 1)   # ROA (%)
PV_UNI  = np.arange(-100, 201, 1)   # PRICE VAR (%)

# ------------ Antecedents & Consequent ------------
profit_margin = ctrl.Antecedent(PM_UNI, 'Profit Margin')
debt_ratio    = ctrl.Antecedent(DR_UNI, 'Debt Ratio')
roa           = ctrl.Antecedent(ROA_UNI, 'ROA')
price_var     = ctrl.Consequent(PV_UNI, 'PRICE VAR [%]')

# Trapezoidal/triangular membership functions (similar to your files)
profit_margin['very low'] = fuzz.trapmf(PM_UNI,  [-200, -200, -150,  -50])
profit_margin['low']      = fuzz.trapmf(PM_UNI,  [-100,  -50,    0,   50])
profit_margin['medium']   = fuzz.trapmf(PM_UNI,  [    0,   25,   75,  100])
profit_margin['high']     = fuzz.trapmf(PM_UNI,  [   50,  100,  150,  200])
profit_margin['very high']= fuzz.trapmf(PM_UNI,  [  150,  200,  200,  200])

debt_ratio['very low'] = fuzz.trapmf(DR_UNI, [0, 0, 10, 20])
debt_ratio['low']      = fuzz.trapmf(DR_UNI, [10, 20, 40, 50])
debt_ratio['medium']   = fuzz.trapmf(DR_UNI, [30, 40, 60, 70])
debt_ratio['high']     = fuzz.trapmf(DR_UNI, [50, 60, 80, 90])
debt_ratio['very high']=fuzz.trapmf(DR_UNI, [80, 90,100,100])

roa['very low']  = fuzz.trapmf(ROA_UNI, [-100, -100,  -75,  -25])
roa['low']       = fuzz.trapmf(ROA_UNI, [  -50,  -25,    0,   25])
roa['medium']    = fuzz.trapmf(ROA_UNI, [    0,   10,   30,   40])
roa['high']      = fuzz.trapmf(ROA_UNI, [   20,   30,   50,   60])
roa['very high'] = fuzz.trapmf(ROA_UNI, [   50,   60,  100,  100])

price_var['big decrease'] = fuzz.trapmf(PV_UNI, [-100, -100,  -75,  -75])
price_var['decrease']     = fuzz.trapmf(PV_UNI, [  -75,  -60,  -40,  -10])
price_var['stable']       = fuzz.trapmf(PV_UNI, [  -10,  -10,   10,   10])
price_var['increase']     = fuzz.trapmf(PV_UNI, [   10,   40,   60,   80])
price_var['big increase'] = fuzz.trapmf(PV_UNI, [   80,  120,  200,  200])

# ------------ Compact, readable rule base ------------
# Intuition:
# - Good profitability/ROA with low debt -> increase
# - Poor profitability/ROA or very high debt -> decrease
# - Otherwise stable
rules = [
    # Strong positive scenarios
    ctrl.Rule( (profit_margin['high'] | profit_margin['very high']) & (roa['high'] | roa['very high']) & (debt_ratio['very low'] | debt_ratio['low']), price_var['big increase'] ),
    ctrl.Rule( (profit_margin['high'] | roa['high']) & (debt_ratio['low'] | debt_ratio['medium']), price_var['increase'] ),

    # Negative leverage/weak fundamentals
    ctrl.Rule( (profit_margin['very low'] | roa['very low']) & (debt_ratio['high'] | debt_ratio['very high']), price_var['big decrease'] ),
    ctrl.Rule( (profit_margin['low'] | roa['low']) & (debt_ratio['medium'] | debt_ratio['high']), price_var['decrease'] ),

    # Mixed cases
    ctrl.Rule( profit_margin['medium'] & debt_ratio['medium'] & roa['medium'], price_var['stable'] ),
    ctrl.Rule( profit_margin['medium'] & (roa['high'] | roa['very high']) & (debt_ratio['low'] | debt_ratio['very low']), price_var['increase'] ),
    ctrl.Rule( profit_margin['medium'] & (roa['low'] | roa['very low']) & (debt_ratio['high'] | debt_ratio['very high']), price_var['decrease'] ),

    # Very high debt often suppresses upside
    ctrl.Rule( (debt_ratio['very high']) & (profit_margin['high'] | roa['high']), price_var['stable'] ),
]

def make_simulation():
    """Return a fresh ControlSystemSimulation ready to take inputs."""
    system = ctrl.ControlSystem(rules)
    return ctrl.ControlSystemSimulation(system)


# ------------------- Fuzzy Calculation Function -------------------
def calculate(pm_value, dr_value, roa_value):
    # Create control system rules
    rule1 = ctrl.Rule(profit_margin['high'] & debt_ratio['low'] & roa['high'], price_var['high'])
    rule2 = ctrl.Rule(profit_margin['low'] & debt_ratio['high'] & roa['low'], price_var['low'])
    # Add more rules here as per your original setup...

    # Create control system
    pricing_ctrl = ctrl.ControlSystem([rule1, rule2])
    pricing = ctrl.ControlSystemSimulation(pricing_ctrl)

    # Pass inputs
    pricing.input['Profit Margin'] = pm_value
    pricing.input['Debt Ratio'] = dr_value
    pricing.input['ROA'] = roa_value

    # Compute
    pricing.compute()

    return pricing.output['PRICE VAR [%]']


def run_fuzzy_model():
    # Replace with actual fuzzy computation
    labels = ["T1", "T2", "T3", "T4", "T5"]
    values = [10, 12, 15, 14, 18]
    return {"labels": labels, "values": values}
