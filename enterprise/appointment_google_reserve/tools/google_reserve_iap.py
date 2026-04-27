# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests
import pytz

from pathlib import Path
from werkzeug.urls import url_join

from odoo import fields
from odoo.exceptions import AccessError
from odoo.addons.iap.tools.iap_tools import iap_jsonrpc, IAPServerError
from odoo.tools import file_open_temporary_directory

_logger = logging.getLogger(__name__)


class GoogleReserveIAP:

    # ------------------------------------------------------------
    # MERCHANTS / SERVICES
    # ------------------------------------------------------------

    def register_appointment(self, appointment_type):
        """ Notify IAP we want to sync an appointment with Google Reserve.

        Here is the merchant information that Google needs:
        - Name (required)
        - Business Category (required)
        - Phone (optional)
        - Website (optional - but 'highly recommended')
        - Full Address (required):
          - Longitude / Latitude (optional unless postal address is not specified)
          - Postal Address (optional unless lon/lat is not specified)
            - Country (required)
            - City (required) ("Locality" in Google documentation)
            - Region (optional)
            - Zip (required) ("Postal Code" in Google documentation)
            - Street Address (required)

        Full objects definition available here:
        - https://developers.google.com/actions-center/verticals/reservations/e2e/reference/feeds/merchants-feed
        - https://developers.google.com/actions-center/verticals/reservations/e2e/reference/feeds/services-feed """

        if not appointment_type.google_reserve_merchant_id:
            raise ValueError("You have to specify an appointment type that has a configured merchant.")

        merchant = appointment_type.google_reserve_merchant_id

        iap_jsonrpc(
            url_join(
                merchant._get_google_reserve_iap_endpoint(),
                "/api/google_reserve/1/appointment/register"
            ),
            params={
                "db_uuid": appointment_type.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                "merchant_details": self._format_merchant_details(merchant),
                "appointment_details": {
                    "appointment_type_id": appointment_type.id,
                    "google_reserve_access_token": appointment_type.google_reserve_access_token,
                    # TODO: Google accepts a list of localized terms, should be able to pass a list of (locale, label)
                    "service_name": appointment_type.name,
                    "min_cancellation_hours": appointment_type.min_cancellation_hours,
                    "min_schedule_hours": appointment_type.min_schedule_hours,
                },
            },
        )

    def unregister_appointment(self, appointment_type):
        """ Notify IAP we want to remove an appointment that was synced with Google Reserve """

        merchant = appointment_type.google_reserve_merchant_id
        iap_jsonrpc(
            url_join(
                merchant._get_google_reserve_iap_endpoint(),
                f"/api/google_reserve/1/appointment/{appointment_type.google_reserve_access_token}/unregister"
            ),
            params={
                "db_uuid": appointment_type.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            },
        )

    def update_merchant(self, merchant):
        """ Notify IAP to sync an updated Merchant """

        iap_jsonrpc(
            url_join(
                merchant._get_google_reserve_iap_endpoint(),
                "/api/google_reserve/1/merchant/update"
            ),
            params={
                "db_uuid": merchant.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                "merchant_details": self._format_merchant_details(merchant),
            },
        )

    # ------------------------------------------------------------
    # AVAILABILITIES
    # ------------------------------------------------------------

    def update_availabilities(self, appointment_types, start_time, end_time):
        """ Replace the availabilities of the appointment types. """
        for appointment_type in appointment_types:
            start_time = start_time.astimezone(pytz.utc)
            end_time = end_time.astimezone(pytz.utc)

            availabilities = appointment_type._google_reserve_get_availabilities(
                start_time=start_time,
                end_time=end_time
            )

            # python datetime isoformat doesn't respect the "RFC3339 UTC 'Zulu' format"
            # which is enforced by Google
            # there does not seem to be another way to do it than a 'dirty' replace
            data = {
                "db_uuid": appointment_types.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                "availabilities": availabilities,
                "start_time": start_time.isoformat().replace('+00:00', 'Z'),  # UTC (RFC3339)
                "end_time": end_time.isoformat().replace('+00:00', 'Z'),  # UTC (RFC3339)
            }

            try:
                iap_jsonrpc(
                    url_join(
                        appointment_types.env['google.reserve.merchant']._get_google_reserve_iap_endpoint(),
                        f"/api/google_reserve/1/appointment/{appointment_type.sudo().google_reserve_access_token}/update_availabilities"
                    ),
                    params=data,
                    timeout=5,
                )
            except (IAPServerError, AccessError) as e:
                _logger.warning("Could not update availabilities: %s", e)

    # ------------------------------------------------------------
    # BOOKINGS
    # ------------------------------------------------------------

    def update_booking(self, appointment_type, calendar_event_ids, event_update_values):
        """ Update Google booking based on write values.

        Note: Google wants a 'start' and a 'duration', not a 'stop' key, hence some basic
        computation inside the method to deduce those."""

        if not appointment_type.google_reserve_enable:
            return

        booking_values = {}
        if event_update_values.get('active') is False:
            booking_values['status'] = "CANCELED"

        if 'start' in event_update_values:
            start = event_update_values['start']
            if isinstance(start, str):
                start = fields.Datetime.from_string(start)
            booking_values['startTime'] = start.isoformat() + 'Z'

            if 'stop' in event_update_values and 'duration' not in event_update_values:
                # manually compute duration
                stop = event_update_values['stop']
                if isinstance(stop, str):
                    stop = fields.Datetime.from_string(stop)
                booking_values['duration'] = str(int((stop - start).total_seconds())) + 's'

        if 'duration' in event_update_values:
            booking_values['duration'] = str(event_update_values['duration'] * 3600) + 's'

        if 'resource_total_capacity_reserved' in event_update_values:
            booking_values['partySize'] = str(event_update_values['resource_total_capacity_reserved'])

        if not booking_values:
            return

        try:
            iap_jsonrpc(
                url_join(
                    appointment_type.env['google.reserve.merchant']._get_google_reserve_iap_endpoint(),
                    f"/api/google_reserve/1/appointment/{appointment_type.sudo().google_reserve_access_token}/update_booking"
                ),
                params={
                    'booking_ids': calendar_event_ids,
                    'booking_values': booking_values,
                    'db_uuid': appointment_type.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                },
                timeout=5,
            )
        except (IAPServerError, AccessError) as e:
            _logger.warning("Could not update booking: %s", e)

    # ------------------------------------------------------------
    # FEED
    # ------------------------------------------------------------

    def upload_availabilities_feed(self, merchants):
        """ Send the appointment availabilities to the IAP Google Reserve service.
         It will then consolidate all availabilities from all Odoo Merchants before uploading
         the complete data to the Google servers. """

        for merchant in merchants:
            try:
                now = merchant.env.cr.now()
                availabilities_by_token = {}

                google_reserve_appointment_types = merchant.appointment_type_ids.filtered('google_reserve_enable')
                if not google_reserve_appointment_types:
                    continue

                for appointment_type in google_reserve_appointment_types:
                    availabilities = appointment_type._google_reserve_get_availabilities()
                    availabilities_by_token[appointment_type.google_reserve_access_token] = availabilities

                json_content = json.dumps(availabilities_by_token)
                filename = f"availabilities_feed_{int(now.timestamp())}.json"
                with file_open_temporary_directory(merchant.env) as temp_dir:
                    local_path = f"{temp_dir}/{filename}"
                    path = Path(local_path)
                    path.write_text(json_content, encoding="utf-8")

                    res = requests.post(
                        url_join(
                            merchant._get_google_reserve_iap_endpoint(),
                            '/api/google_reserve/1/merchant/upload_availabilities_feed',
                        ),
                        data={
                            'db_uuid': merchant.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                            'merchant_id': merchant.id,
                        },
                        files={'upload_file': path.open()},
                        timeout=120,
                    )

                if not res.ok:
                    _logger.warning("Could not upload availability feed: %s", res.text)
            except requests.exceptions.RequestException as e:
                _logger.warning("Could not upload availability feed: %s", e)

    # ------------------------------------------------------------
    # UTILS
    # ------------------------------------------------------------

    def _format_merchant_details(self, merchant):
        return {
            "name": merchant.name,
            "id": merchant.id,
            "callback_url": merchant.get_base_url(),
            "business_category": merchant.business_category,
            "phone": merchant.phone_sanitized,
            "website_url": merchant.website_url,
            "location": {
                "country_code": merchant.location_id.country_id.code,
                "city": merchant.location_id.city,
                "region": merchant.location_id.state_id.code or False,
                "zip": merchant.location_id.zip,
                "street": merchant.location_id.street,
            }
        }
