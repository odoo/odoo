from datetime import datetime
from dateutil.relativedelta import relativedelta


def get_based_on_date_range(based_on):
    start_date = limit_date = datetime.now()
    if not based_on or based_on == 'actual_demand' or based_on == '30_days':
        start_date = start_date - relativedelta(days=30)  # Default monthly demand
    elif based_on == 'one_week':
        start_date = start_date - relativedelta(weeks=1)
    elif based_on == 'three_months':
        start_date = start_date - relativedelta(months=3)
    elif based_on == 'one_year':
        start_date = start_date - relativedelta(years=1)
    else:  # Relative period of time.
        today = datetime.now()
        start_date = datetime(year=today.year - 1, month=today.month, day=1)

        if based_on == 'last_year_m_plus_1':
            start_date += relativedelta(months=1)
        elif based_on == 'last_year_m_plus_2':
            start_date += relativedelta(months=2)

        if based_on == 'last_year_quarter':
            limit_date = start_date + relativedelta(months=3)
        else:
            limit_date = start_date + relativedelta(months=1)

    return {
        "suggest_based_on": based_on,
        "monthly_demand_start": start_date,
        "monthly_demand_limit": limit_date,
    }
