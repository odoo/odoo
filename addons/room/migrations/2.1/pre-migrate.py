"""The kiosk moved from the booking profile onto the resource itself, and
calendar's 2.4 script repointed every profile xml id to that resource. The demo
rooms are still named after the profile they no longer have; rename them before
this module's data loads, or the demo file adopts nothing and creates a second
set of rooms beside them."""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
           SET name = regexp_replace(name, '_profile$', '_resource')
         WHERE module = 'room'
           AND model = 'resource.resource'
           AND name LIKE '%\\_profile'
        """
    )
