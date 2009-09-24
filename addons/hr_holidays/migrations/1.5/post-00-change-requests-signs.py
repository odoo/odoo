__name__ = "Change signs of old holiday requests"

def migrate(cr, version):
    cr.execute("DELETE FROM hr_holidays WHERE number_of_days < 0")
    cr.execute("UPDATE hr_holidays SET number_of_days = -number_of_days, type ='remove'")
