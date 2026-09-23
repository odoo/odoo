import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class DeviceDeviceController(http.Controller):
    # csrf=False: auth="receiver" admits the caller through its inbound gate
    @http.route(
        "/remote/device/<string:identifier>/data",
        type="http",
        auth="receiver",
        receiver="device.device:_receiver_for_identifier",
        receiver_event="device_push",
        methods=["POST"],
        csrf=False,
        save_session=False,
        typed=True,
    )
    def device_push_data(self, identifier: str, **kwargs):
        admission = request.admission
        device = admission.subject
        data = admission.json()

        try:
            if device.processing_mode == "async":
                device.queue_event(
                    data,
                    metadata={
                        "source_ip": admission.remote_addr,
                        "source": "http_push",
                    },
                    event_log=admission.exchange,
                )
                device._touch_last_seen()
                return request.prepare_json_response(
                    {
                        "status": "accepted",
                        "message": "Data queued for processing",
                        "device_name": device.name,
                    },
                    status=202,
                )
            device._store_push_data_point(data)
            admission.settle()
            return request.prepare_json_response(
                {
                    "status": "success",
                    "message": "Data received and stored successfully",
                    "device_name": device.name,
                }
            )
        except Exception as error:
            _logger.exception("Error processing device data")
            admission.settle(str(error), retry=True)
            return request.prepare_json_response(
                {"error": "processing_error", "message": "Failed to process data"},
                status=500,
            )

    @http.route(
        "/remote/device/<string:identifier>/status",
        type="http",
        auth="receiver",
        receiver="device.device:_receiver_for_identifier",
        receiver_event="device_status",
        methods=["GET"],
        save_session=False,
        typed=True,
    )
    def device_get_status(self, identifier: str, **kwargs):
        device = request.admission.subject
        return request.prepare_json_response(
            {
                "status": "success",
                "device": {
                    "identifier": device.identifier,
                    "name": device.name,
                    "connection_state": device.connection_state,
                    "last_data_received": (
                        device.date_last_data_received.isoformat()
                        if device.date_last_data_received
                        else None
                    ),
                    "active": device.active,
                    "category": device.device_category_id.name or None,
                },
            }
        )
