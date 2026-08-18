# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlencode, urlsplit

from odoo.http import request

from odoo.addons.payment.controllers import portal as payment_portal


class Attributes(payment_portal.PaymentPortal):
    def _get_attribute_value_params(self, query_params):
        """Extract the attribute value query params from a dict of more general query params.

        Attribute value query params are expected to have the following format:
        `attribute-name-1=attribute-value-name-2,attribute-value-name-3`

        :param dict(str, str) query_params: The more general query params from which to extract the
            attribute value query params.
        :return: A dict of attribute value query params.
        :rtype: dict(str, str)
        """
        unslug = self.env["ir.http"]._unslug
        # Only keep the query params whose key can be unslugged (meaning that the key is an
        # attribute slug).
        return {
            attr: attr_values
            for attr, attr_values in query_params.items()
            if unslug(attr)[1] and attr_values
        }

    def _get_attribute_value_dict(self, attribute_value_params):
        """Return a dict mapping attribute IDs to lists of attribute value IDs, from a dict of
        attribute value query params.

        Attribute value query params are expected to have the following format:
        `attribute-name-1=attribute-value-name-2,attribute-value-name-3`

        This method will ignore any invalid attributes and attribute values (we don't want to raise
        errors for invalid query params). Moreover, it will only consider the first occurrence of a
        given attribute (other occurrences are ignored).

        :param dict(str, str) attribute_value_params: The attribute value query params from which to
            compute the mapping.
        :return: A dict mapping attribute IDs to lists of attribute value IDs.
        :rtype: dict(int, list(int))
        """
        unslug = self.env["ir.http"]._unslug
        # For each attribute value query param, unslug its key (attribute)
        # and value (attribute values).
        attribute_value_dict = {}
        for attr, attr_values in attribute_value_params.items():
            attr_id = unslug(attr)[1]
            attribute = self.env["product.attribute"].browse(attr_id).exists()
            if not attribute:
                continue

            if attribute.display_type == "range":
                pavs = attribute.value_ids.sorted("sequence")
                min_slug, _separator, max_slug = attr_values.partition("<")
                min_id = unslug(min_slug)[1]
                max_id = unslug(max_slug)[1]

                if min_id not in pavs._ids or max_id not in pavs._ids:
                    continue

                min_index = pavs._ids.index(min_id)
                max_index = pavs._ids.index(max_id)
                attribute_value_dict[attr_id] = pavs._ids[min_index : max_index + 1]
                continue

            value_ids = []
            for attr_value in attr_values.split(","):
                if value_id := unslug(attr_value)[1]:
                    value_ids.append(value_id)  # noqa: PERF401

            if value_ids:
                attribute_value_dict[attr_id] = value_ids

        return attribute_value_dict

    def _get_url_with_attribute_values(self, grouped_attributes_values):
        """Return the current request's URL, but replace the attribute value query params with
        `grouped_attributes_values` (formatted as query params).
        """
        query = request.httprequest.args.to_dict(flat=False)
        query.pop("attribute_values", None)
        slug = self.env["ir.http"]._slug
        for pa, pavs in grouped_attributes_values.items():
            query[slug(pa)] = ",".join([slug(pav) for pav in pavs])
        url = urlsplit(request.httprequest.url)
        return url._replace(query=urlencode(query, doseq=True)).geturl()
