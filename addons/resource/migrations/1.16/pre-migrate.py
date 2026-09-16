def migrate(cr, version):
    if not version:
        return
    # One custody role: a vehicle's driver is the operator of a vehicle.
    cr.execute("UPDATE resource_assignment SET role = 'operator' WHERE role = 'driver'")
