import logging

import requests


_logger = logging.getLogger(__name__)


class KsefLatarniaService:

    def __init__(self, env):
        mode = env['ir.config_parameter'].sudo().get_param('l10n_pl_edi_ksef.mode') or 'prod'
        # The test Latarnia always answers the TOTAL_FAILURE demo scenario, so test mode is stubbed as available.
        self.test_mode = mode == 'test'
        self.api_url = "https://api-latarnia.ksef.mf.gov.pl"

    def _get(self, endpoint):
        try:
            response = requests.get(
                f'{self.api_url}/{endpoint}',
                headers={'Accept': 'application/json'},
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError):
            _logger.warning(
                "Could not retrieve KSeF availability information from %s.",
                endpoint,
                exc_info=True,
            )
            return None

    def get_status(self):
        if self.test_mode:
            return {'status': 'AVAILABLE'}
        data = self._get('status')
        return data if isinstance(data, dict) else None

    def get_messages(self):
        if self.test_mode:
            return []
        data = self._get('messages')
        return data if isinstance(data, list) else None
