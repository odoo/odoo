from odoo import models, _
from odoo.exceptions import ValidationError


class EventTicket(models.Model):
    _inherit = 'event.event.ticket'
    _order = "event_id, sequence, price, name, id"

    def _lock_and_check_availability(self, ticket_qtys):
        if not self.ids or not ticket_qtys:
            return

        event_ids = tuple({ticket.event_id.id for ticket in self})

        self._cr.execute(
            "SELECT id, seats_max, seats_limited FROM event_event WHERE id IN %s FOR UPDATE",
            (event_ids,),
        )
        events_data = {row[0]: {'seats_max': row[1], 'seats_limited': row[2]} for row in self._cr.fetchall()}

        self._cr.execute(
            f"SELECT id, seats_max FROM {self._table} WHERE id IN %s FOR UPDATE",
            (tuple(self.ids),),
        )
        tickets_data = {row[0]: row[1] for row in self._cr.fetchall()}

        new_cr = self.pool.cursor()
        try:
            new_cr.execute(
                """SELECT event_ticket_id, COUNT(*)
                     FROM event_registration
                    WHERE event_ticket_id IN %s
                      AND (state IN ('open', 'done') OR sale_status = 'sold')
                      AND active = true
                 GROUP BY event_ticket_id""",
                (tuple(self.ids),),
            )
            ticket_counts = dict(new_cr.fetchall())

            new_cr.execute(
                """SELECT event_id, COUNT(*)
                     FROM event_registration
                    WHERE event_id IN %s
                      AND (state IN ('open', 'done') OR sale_status = 'sold')
                      AND active = true
                 GROUP BY event_id""",
                (event_ids,),
            )
            event_counts = dict(new_cr.fetchall())
        finally:
            new_cr.close()

        event_qtys = {}
        for ticket, qty in ticket_qtys.items():
            event_qtys[ticket.event_id.id] = event_qtys.get(ticket.event_id.id, 0) + qty

        sold_out = []
        checked_events = set()

        for ticket, qty in ticket_qtys.items():
            ticket_seats_max = tickets_data.get(ticket.id, 0)
            if ticket_seats_max:
                available = ticket_seats_max - ticket_counts.get(ticket.id, 0)
                if available < qty:
                    sold_out.append(_(
                        '- the ticket "%(ticket_name)s" (%(event_name)s): Missing %(nb_too_many)i seats.',
                        ticket_name=ticket.name,
                        event_name=ticket.event_id.name,
                        nb_too_many=qty - available,
                    ))

            event_id = ticket.event_id.id
            if event_id not in checked_events:
                checked_events.add(event_id)
                data = events_data.get(event_id, {})
                event_seats_max = data.get('seats_max', 0)
                if data.get('seats_limited') and event_seats_max:
                    available = event_seats_max - event_counts.get(event_id, 0)
                    if available < event_qtys[event_id]:
                        sold_out.append(_(
                            '- "%(event_name)s": Missing %(nb_too_many)i seats.',
                            event_name=ticket.event_id.name,
                            nb_too_many=event_qtys[event_id] - available,
                        ))

        if sold_out:
            raise ValidationError(_('There are not enough seats available for:\n%s', '\n'.join(sold_out)))

    def _get_ticket_multiline_description(self):
        """ If people set a description on their product it has more priority
        than the ticket name itself for the SO description. """
        self.ensure_one()
        if self.product_id.description_sale:
            return '%s\n%s' % (self.product_id.description_sale, self.event_id.display_name)
        return super(EventTicket, self)._get_ticket_multiline_description()
