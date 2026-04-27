# Part of Odoo. See LICENSE file for full copyright and licensing details.

class IrnException(Exception):
    """
    Exception class for handling IRN-related errors.

    This class extends the built-in Exception to format and manage errors related
    to IRN (Invoice Reference Number) processing.
    """

    def __init__(self, errors):
        """
        Initializes the IrnException with formatted error messages.
        """
        self.errors = errors
        super().__init__(self._format_errors())

    def _format_errors(self):
        """
        Formats the error messages for display.

        Converts the errors into a readable format. If the error code is 'no-credit',
        a specific message related to IAP buy credits is returned.
        """
        if isinstance(self.errors, dict):
            self.errors['code'] = self.errors.pop('error_cd', None)
            self.errors = [self.errors]
        error_codes = [e.get('code') for e in self.errors]
        if 'no-credit' in error_codes:
            return 'no-credit'
        return '\n'.join(["[%s] %s" % (e.get("code"), e.get("message")) for e in self.errors])
