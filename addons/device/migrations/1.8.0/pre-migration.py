def migrate(cr, version):
    # remote.device.latitude/longitude were editable on the form and read by
    # nothing: the map takes its position from log_gps_last_id.the_point, so
    # anything typed here was silently ignored. Anything a database does hold is
    # folded into the free-text location it sat beside, then the columns go.
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'remote_device' AND column_name = 'latitude'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        UPDATE remote_device
           SET location = trim(both ' ' from
                   coalesce(location, '') || ' (' ||
                   round(latitude::numeric, 7) || ', ' ||
                   round(longitude::numeric, 7) || ')')
         WHERE coalesce(latitude, 0) <> 0 OR coalesce(longitude, 0) <> 0
        """
    )
    cr.execute("ALTER TABLE remote_device DROP COLUMN latitude, DROP COLUMN longitude")
    cr.execute(
        """
        DELETE FROM ir_model_fields
         WHERE model = 'remote.device' AND name IN ('latitude', 'longitude')
        """
    )
