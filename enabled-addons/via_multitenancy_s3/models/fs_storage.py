import logging
from odoo import models, api
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)


class FsStorageMultitenant(models.Model):
    _inherit = 'fs.storage'
    
    @api.model
    def _get_tenant_from_db(self):
        """
        Extract tenant identifier from database name.
        
        Examples:
            via-suite-nissei -> nissei
            via-suite-cellshop -> cellshop
            via-suite-megaeletronicos -> megaeletronicos
        
        Returns:
            str: Tenant identifier
        """
        db_name = self.env.cr.dbname
        
        # Remove prefix "via-suite-"
        if db_name.startswith('via-suite-'):
            tenant = db_name.replace('via-suite-', '')
        else:
            # Fallback for non-standard DB names
            tenant = db_name
            _logger.warning(
                f"DB name '{db_name}' doesn't match expected pattern 'via-suite-*'. "
                f"Using '{tenant}' as tenant identifier."
            )
        
        # Validate tenant name (security)
        if '/' in tenant or '..' in tenant:
            raise AccessError(f"Invalid tenant name: {tenant}")
        
        return tenant
    
    def _get_path(self, attachment):
        """
        Override to add tenant prefix to S3 paths.
        
        Original path: attachments/{checksum}/{filename}
        New path:      tenants/{tenant}/attachments/{checksum}/{filename}
        
        Args:
            attachment: ir.attachment record
            
        Returns:
            str: S3 path with tenant prefix
        """
        tenant = self._get_tenant_from_db()
        base_path = super()._get_path(attachment)
        
        # Add tenant prefix
        tenant_path = f"tenants/{tenant}/{base_path}"
        
        _logger.debug(
            f"[MULTITENANCY] Generated S3 path for tenant '{tenant}': {tenant_path}"
        )
        
        return tenant_path
    
    def _validate_path_access(self, path):
        """
        Validate that current tenant can access requested path.
        Prevents path traversal attacks and cross-tenant access.
        
        Args:
            path (str): S3 path to validate
            
        Raises:
            AccessError: If path doesn't belong to current tenant
        """
        tenant = self._get_tenant_from_db()
        expected_prefix = f"tenants/{tenant}/"
        
        if not path.startswith(expected_prefix):
            _logger.warning(
                f"[SECURITY] Access denied: Tenant '{tenant}' tried to access path '{path}'"
            )
            raise AccessError(
                f"Access denied: Path '{path}' does not belong to tenant '{tenant}'"
            )
        
        # Additional validation: no path traversal
        if '..' in path or '//' in path:
            _logger.error(
                f"[SECURITY] Path traversal attempt detected: {path}"
            )
            raise AccessError(f"Invalid path: {path}")
    
    def _get_url(self, path):
        """
        Override to validate path before generating URL.
        
        Args:
            path (str): S3 path
            
        Returns:
            str: Signed URL
        """
        self._validate_path_access(path)
        return super()._get_url(path)
    
    def _read(self, path):
        """
        Override to validate path before reading.
        
        Args:
            path (str): S3 path
            
        Returns:
            bytes: File content
        """
        self._validate_path_access(path)
        return super()._read(path)
    
    def _write(self, path, data):
        """
        Override to validate path before writing.
        
        Args:
            path (str): S3 path
            data (bytes): File content
        """
        self._validate_path_access(path)
        return super()._write(path, data)
    
    def _delete(self, path):
        """
        Override to validate path before deleting.
        
        Args:
            path (str): S3 path
        """
        self._validate_path_access(path)
        return super()._delete(path)
