import logging
import socket
import urllib
from datetime import datetime

import requests
from woocommerce import API

from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.exception import NetworkRetryableError, RetryableJobError

_logger = logging.getLogger(__name__)


class WooLocation(object):
    """The Class is used to set Location"""

    def __init__(self, location, client_id, client_secret, version, test_mode):
        """Initialization to set location"""
        self._location = location
        self.client_id = client_id
        self.client_secret = client_secret
        self.version = version
        self.test_mode = test_mode

    @property
    def location(self):
        return self._location


class WooAPI(object):
    def __init__(self, location):
        """
        :param location: Remote location
        :type location: :class:`GenericLocation`
        """
        self._location = location
        self._api = None

    @property
    def api(self):
        if self._api is None:
            woocommerce_client = API(
                url=self._location.location,
                consumer_key=self._location.client_id,
                consumer_secret=self._location.client_secret,
                version=self._location.version,
                wp_api=True,
            )
            self._api = woocommerce_client
        return self._api

    def api_call(self, resource_path, arguments, http_method=None):
        """Adjust available arguments per API"""
        if not self.api:
            return self.api
        http_method = http_method.lower()
        additional_data = {}
        if http_method == "get":
            additional_data.update(params=arguments)
        else:
            additional_data.update(data=arguments)
        return getattr(self.api, http_method)(resource_path, **additional_data)

    def __enter__(self):
        # we do nothing, api is lazy
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._api is not None and hasattr(self._api, "__exit__"):
            self._api.__exit__(exc_type, exc_value, traceback)

    def call(self, resource_path, arguments, http_method=None):
        try:
            if isinstance(arguments, list):
                while arguments and arguments[-1] is None:
                    arguments.pop()
            start = datetime.now()
            try:
                result = self.api_call(
                    resource_path, arguments, http_method=http_method
                )
            except Exception:
                _logger.error("api.call('%s', %s) failed", resource_path, arguments)
                raise
            else:
                _logger.debug(
                    "api.call('%s', %s) returned %s in %s seconds",
                    resource_path,
                    arguments,
                    result,
                    (datetime.now() - start).seconds,
                )
            status_code = result.status_code
            if status_code == 201:
                return result.json()
            if status_code == 200:
                json_response = result.json()
                record_count = result.headers.get("X-WP-Total")
                return {"record_count": record_count, "data": json_response}
            if (
                status_code == 400
                or status_code == 401
                or status_code == 404
                or status_code == 500
            ):
                # From Woo on invalid data we get a 400 error
                # From Woo on Authentication or permission error we get a 401 error,
                # e.g. incorrect API keys
                # From Woo on record don't exist or are missing we get a 404 error
                # but raise_for_status treats it as a network error (which is retryable)
                raise requests.HTTPError(
                    self._location.location,
                    result.status_code,
                    result._content,
                    __name__,
                )
            result.raise_for_status()
            return result
        except (socket.gaierror, socket.error, socket.timeout) as err:
            raise NetworkRetryableError(
                "A network error caused the failure of the job: " "%s" % err
            ) from err
        except urllib.error.HTTPError as err:
            if err.code in [502, 503, 504]:
                # Origin Error
                raise RetryableJobError(
                    "HTTP Error:\n"
                    "Code: %s\n"
                    "Reason: %s\n"
                    "Headers: %d\n" % (err.code, err.reason, err.headers)
                ) from err
            else:
                raise


class WooCRUDAdapter(AbstractComponent):
    """External Records Adapter for Woocommerce"""

    # pylint: disable=method-required-super

    _name = "woo.crud.adapter"
    _inherit = ["base.backend.adapter", "connector.woo.base"]
    _usage = "backend.adapter"

    def search(self, filters=None, **kwargs):
        """
        Search records according to some criterias
        and returns a list of ids
        """
        raise NotImplementedError

    def read(self, external_id, attributes=None):
        """Returns the information of a record"""
        raise NotImplementedError

    def search_read(self, filters=None, **kwargs):
        """
        Search records according to some criterias
        and returns their information
        """
        raise NotImplementedError

    def create(self, data, **kwargs):
        """Create a record on the external system"""
        raise NotImplementedError

    def write(self, external_id, data, **kwargs):
        """Update records on the external system"""
        raise NotImplementedError

    def delete(self, external_id, **kwargs):
        """Delete a record on the external system"""
        raise NotImplementedError

    def _call(self, resource_path, arguments=None, http_method=None):
        """Method to initiate the connection"""
        try:
            woo_api = getattr(self.work, "woo_api", None)
        except AttributeError:
            raise AttributeError(
                "You must provide a woo_api attribute with a "
                "WooAPI instance to be able to use the "
                "Backend Adapter."
            ) from None
        return woo_api.call(
            resource_path=resource_path, arguments=arguments, http_method=http_method
        )


class GenericAdapter(AbstractComponent):
    # pylint: disable=method-required-super

    _name = "woo.adapter"
    _inherit = "woo.crud.adapter"
    _apply_on = "woo.backend"
    _last_update_date = "date_modified_gmt"
    _woo_model = None
    _check_import_sync_date = False
    _woo_ext_id_key = "id"
    _odoo_ext_id_key = "external_id"

    def search(self, filters=None, **kwargs):
        """Method to get the records from woo"""
        result = self._call(
            resource_path=self._woo_model, arguments=filters, http_method="get"
        )
        if kwargs.get("_woo_product_stock", False):
            setting_stock_result = self._call(
                resource_path=kwargs.get("_woo_product_stock"),
                arguments=filters,
                http_method="get",
            )
            result["data"].append(setting_stock_result.get("data", []))

        if kwargs.get("_woo_default_currency", False):
            default_currency_result = self._call(
                resource_path=kwargs.get("_woo_default_currency"),
                arguments=filters,
                http_method="get",
            )
            result["data"].append(default_currency_result.get("data"))

        if kwargs.get("_woo_default_weight", False):
            default_weight_result = self._call(
                resource_path=kwargs.get("_woo_default_weight"),
                arguments=filters,
                http_method="get",
            )
            result["data"].append(default_weight_result.get("data"))

        if kwargs.get("_woo_default_dimension", False):
            default_dimension_result = self._call(
                resource_path=kwargs.get("_woo_default_dimension"),
                arguments=filters,
                http_method="get",
            )
            result["data"].append(default_dimension_result.get("data"))

        return result

    def read(self, external_id=None, attributes=None, **kwargs):
        """Method to get a data for specified record"""
        resource_path = "{}/{}".format(self._woo_model, external_id)
        result = self._call(resource_path=resource_path, http_method="get")
        result = result.get("data", [])
        return result

    def create(self, data, **kwargs):
        """Creates the data in remote"""
        result = self._call(self._woo_model, arguments=data, http_method="post")
        return result

    def write(self, external_id, data, **kwargs):
        """Update records on the external system"""
        resource_path = "{}/{}".format(self._woo_model, external_id)
        if data.get("template_external_id", False):
            resource_path = "{}/{}/variations/{}".format(
                self._woo_model, data.get("template_external_id"), external_id
            )
            data.pop("template_external_id")
        result = self._call(
            resource_path=resource_path, arguments=data, http_method="put"
        )
        return result
