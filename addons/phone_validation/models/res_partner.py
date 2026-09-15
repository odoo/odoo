from collections.abc import Set as AbstractSet

from odoo import api, models

# What the ORM itself accepts as a multi-value search term, mirroring
# odoo.orm.primitives. An `in` arrives as an OrderedSet, not as a list.
COLLECTION_TYPES = (list, tuple, AbstractSet)


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["mixin.mail.thread.phone", "res.partner"]

    def _phone_replace_number(self, fname, number, *types):
        self.check_singleton()
        current = self._phone_get_number()
        if fname != "phone_ids" or (
            types and current != self._phone_get_number(*types)
        ):
            return super()._phone_replace_number(fname, number, *types)
        if number == current.number:
            return None
        replacement = self.env["phone.number"]
        if number:
            replacement = replacement.create(
                {"number": number, "type": current.type or "mobile"}
            )
        self.write(self._prepare_phone_replacement_vals(replacement))
        return None

    @property
    def _rec_names_search(self):
        return [*super()._rec_names_search, "phone_mobile_search"]

    @api.model
    def _search_display_name_match(self, operator, value, search_fnames):
        """Resolve a short term on the other name fields instead of failing.

        A Many2one autocomplete fires on the first keystroke, and the phone
        search refuses a term below ``_phone_search_min_length``. Left in the
        OR, that refusal takes down the whole lookup, so a contact could no
        longer be picked by typing one or two letters of its name.
        """
        if "phone_mobile_search" in search_fnames and (
            self._phone_term_too_short(value) or not self._phone_term_has_digit(value)
        ):
            search_fnames = [
                fname for fname in search_fnames if fname != "phone_mobile_search"
            ]
        return super()._search_display_name_match(operator, value, search_fnames)

    @api.model
    def _phone_term_has_digit(self, value):
        # a name typed into a many2one is looked up on the phone numbers too,
        # a regexp scan of the whole table per keystroke; a term without a
        # digit cannot name a number, so the scan is not started for it
        values = value if isinstance(value, COLLECTION_TYPES) else [value]
        return any(
            not isinstance(term, str) or any(ch.isdigit() for ch in term)
            for term in values
        )

    @api.model
    def _phone_term_too_short(self, value):
        """Whether a search term is below the minimum the phone search accepts.

        An empty term is not too short: the phone search lets it through as a
        set/unset test rather than rejecting it.
        """
        minimum = self._phone_search_min_length
        if not minimum:
            return False
        values = value if isinstance(value, COLLECTION_TYPES) else [value]
        return any(
            isinstance(term, str) and 0 < len(term.strip()) < minimum for term in values
        )
