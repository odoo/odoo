from odoo import models
from odoo.tools import format_datetime


class MailMessage(models.Model):
    _inherit = "mail.message"

    def _portal_get_default_format_properties_names(self, options=None):
        """Add request for rating information

        :param dict options: supports 'rating_include' option allowing to
          conditionally include rating information;
        """
        properties_names = super()._portal_get_default_format_properties_names(
            options=options
        )
        if options and options.get("rating_include"):
            properties_names |= {
                "rating",
                "rating_value",
            }
        return properties_names

    def _portal_message_format(self, properties_names, options=None):
        """If requested, add rating information to returned formatted values.

        Note: rating information combine both statistics (see 'rating_get_stats'
        if available on model) and rating / publication information."""
        vals_list = super()._portal_message_format(properties_names, options=options)
        if "rating" not in properties_names:
            return vals_list

        # Use the same latest consumed rating as mail.message.rating_value.
        related_rating = self.sudo().rating_id.read(
            [
                "id",
                "publisher_comment",
                "publisher_id",
                "publisher_datetime",
                "message_id",
            ]
        )
        message_to_rating = {
            rating["message_id"][0]: self._portal_message_format_rating(rating)
            for rating in related_rating
        }

        stats_by_record = {}
        messages_by_id = {message.id: message for message in self}
        for values in vals_list:
            # Portal also appends reference rows for linked messages. Those are
            # not part of the rating request and need no rating metadata.
            message = messages_by_id.get(values["id"])
            if message is None:
                continue
            values["rating_id"] = message_to_rating.get(message.id, {})

            if message.model not in self.env or not message.res_id:
                # Messages can outlive their document's module.
                continue
            record_key = (message.model, message.res_id)
            if record_key not in stats_by_record:
                # Several messages commonly point at the same record (e.g. a
                # thread with many comments); compute rating_get_stats() once
                # per record instead of once per message.
                record = self.env[message.model].browse(message.res_id)
                stats_by_record[record_key] = (
                    record.sudo().rating_get_stats()
                    if hasattr(record, "rating_get_stats")
                    else None
                )
            stats = stats_by_record[record_key]
            if stats is not None:
                values["rating_stats"] = stats

        return vals_list

    def _portal_message_format_rating(self, rating_values):
        """From 'rating_values' get an updated version formatted for frontend
        display.

        :param dict rating_values: values coming from reading ratings
          in database;

        :returns: updated rating_values
        :rtype: dict
        """
        publisher_id, publisher_name = rating_values["publisher_id"] or [False, ""]
        rating_values["publisher_avatar"] = (
            f"/web/image/res.partner/{publisher_id}/avatar_128/50x50"
            if publisher_id
            else ""
        )
        rating_values["publisher_comment"] = rating_values["publisher_comment"] or ""
        rating_values["publisher_datetime"] = format_datetime(
            self.env, rating_values["publisher_datetime"]
        )
        rating_values["publisher_id"] = publisher_id
        rating_values["publisher_name"] = publisher_name
        return rating_values
