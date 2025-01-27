import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, padding, rsa
from cryptography.hazmat.primitives.serialization import Encoding

from odoo import _, api, fields, models
from odoo.exceptions import UserError


STR_TO_HASH = {
    'sha1': hashes.SHA1(),
    'sha256': hashes.SHA256(),
}

STR_TO_CURVE = {
    'SECP256R1': ec.SECP256R1(),
}


def _get_formatted_value(data, formatting='encodebytes'):
    if formatting == 'encodebytes':
        return base64.encodebytes(data)
    elif formatting == 'base64':
        return base64.b64encode(data)
    else:
        return data


def _int_to_bytes(value, byteorder='big'):
    return value.to_bytes((value.bit_length() + 7) // 8, byteorder=byteorder)


class Key(models.Model):
    _name = 'certificate.key'
    _description = 'Cryptographic Keys'

    name = fields.Char(string='Name', default="New key")
    content = fields.Binary(string='Key file', required=True)
    password = fields.Char(string='Private key password')
    pem_key = fields.Binary(
        string='Key bytes in PEM format',
        compute='_compute_pem_key',
        store=True,
    )
    public = fields.Boolean(
        string='Public/Private key',
        compute='_compute_pem_key',
        store=True,
    )
    loading_error = fields.Text(
        string='Loading error',
        compute='_compute_pem_key',
        store=True,
    )
    active = fields.Boolean(name='Active', help='Set active to false to archive the key.', default=True)
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        ondelete='cascade',
    )

    @api.depends('content', 'password')
    def _compute_pem_key(self):
        for key in self:
            content = key.with_context(bin_size=False).content
            if not content:
                key.pem_key = None
                key.public = None
                key.loading_error = ""
            else:
                pkey_content = base64.b64decode(content)
                pkey_password = key.password.encode('utf-8') if key.password else None

                # Try to load the key in different format starting with DER then PEM for private then public keys.
                # If none succeeded, we report an error.
                pkey = None
                try:
                    pkey = serialization.load_der_private_key(pkey_content, pkey_password)
                    key.public = False
                except (ValueError, TypeError):
                    pass

                if not pkey:
                    try:
                        pkey = serialization.load_pem_private_key(pkey_content, pkey_password)
                        key.public = False
                    except (ValueError, TypeError):
                        pass

                if not pkey:
                    try:
                        pkey = serialization.load_der_public_key(pkey_content)
                        key.public = True
                    except (ValueError, TypeError):
                        pass

                if not pkey:
                    try:
                        pkey = serialization.load_pem_public_key(pkey_content)
                        key.public = True
                    except (ValueError, TypeError):
                        pass

                if not pkey:
                    key.pem_key = None
                    key.public = None
                    key.loading_error = _("This key could not be loaded. Either its content or its password is erroneous.")
                    continue

                if key.public:
                    key.pem_key = base64.b64encode(pkey.public_bytes(
                        encoding=Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ))
                else:
                    key.pem_key = base64.b64encode(pkey.private_bytes(
                        encoding=Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))

                key.loading_error = ""

    # -------------------------------------------------------
    #                   Business Methods                    #
    # -------------------------------------------------------

    def _sign(self, message, hashing_algorithm='sha256', formatting='encodebytes'):
        """ Return the base64 encoded signature of message. """
        self.ensure_one()

        if self.public:
            raise UserError(_("Make sure to use a private key to sign documents."))

        pem_key = self.with_context(bin_size=False).pem_key
        if self.loading_error:
            raise UserError(self.name + " - " + self.loading_error)

        return self._sign_with_key(
            message,
            pem_key,
            pwd=None,
            hashing_algorithm=hashing_algorithm,
            formatting=formatting
        )

    def _get_public_key_numbers_bytes(self, formatting='encodebytes'):
        self.ensure_one()

        return self._numbers_public_key_bytes_with_key(
            self._get_public_key_bytes(encoding='PEM'),
            formatting=formatting,
        )

    def _get_public_key_bytes(self, encoding='der', formatting='encodebytes'):
        self.ensure_one()

        if self.public:
            public_key = serialization.load_pem_public_key(base64.b64decode(self.with_context(bin_size=False).pem_key))
        else:
            public_key = serialization.load_pem_private_key(base64.b64decode(self.with_context(bin_size=False).pem_key), None).public_key()

        encoding = serialization.Encoding.DER if encoding == 'der' else serialization.Encoding.PEM
        return _get_formatted_value(
            public_key.public_bytes(
                encoding=encoding,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ),
            formatting=formatting,
        )

    def _decrypt(self, message, hashing_algorithm='sha256'):
        self.ensure_one()

        if not isinstance(message, bytes):
            message = message.encode('utf-8')

        if self.public:
            raise UserError(_("A private key is required to decrypt data."))
        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(f"Unsupported hashing algorithm '{hashing_algorithm}'. Currently supported: sha1 and sha256.")

        private_key = serialization.load_pem_private_key(base64.b64decode(self.pem_key), None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise UserError(_("Unsupported asymmetric cryptography algorithm '%s'. Currently supported for decryption: RSA.", type(private_key)))

        return private_key.decrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=STR_TO_HASH[hashing_algorithm]),
                algorithm=STR_TO_HASH[hashing_algorithm],
                label=None
            )
        )

    @api.model
    def _sign_with_key(self, message, pem_key, pwd=None, hashing_algorithm='sha256', formatting='encodebytes'):
        """ Return the base64 encoded signature of message. """

        if not isinstance(message, bytes):
            message = message.encode('utf-8')

        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(f"Unsupported hashing algorithm '{hashing_algorithm}'. Currently supported: sha1 and sha256.")

        try:
            private_key = serialization.load_pem_private_key(base64.b64decode(pem_key), pwd)
        except ValueError:
            raise UserError(_("The private key could not be loaded."))

        if isinstance(private_key, ec.EllipticCurvePrivateKey):
            signature = private_key.sign(
                message,
                ec.ECDSA(STR_TO_HASH[hashing_algorithm])
            )
        elif isinstance(private_key, rsa.RSAPrivateKey):
            signature = private_key.sign(
                message,
                padding.PKCS1v15(),
                STR_TO_HASH[hashing_algorithm]
            )
        else:
            raise UserError(_("Unsupported asymmetric cryptography algorithm '%s'. Currently supported for signature: EC and RSA.", type(private_key)))

        return _get_formatted_value(signature, formatting=formatting)

    @api.model
    def _numbers_public_key_bytes_with_key(self, pem_key, formatting='encodebytes'):
        try:
            public_key = serialization.load_pem_public_key(base64.b64decode(pem_key))
        except ValueError:
            raise UserError(_("The public key could not be loaded."))

        if isinstance(public_key, ec.EllipticCurvePublicKey):
            e = public_key.public_numbers().x
            n = public_key.public_numbers().y
        elif isinstance(public_key, rsa.RSAPublicKey):
            e = public_key.public_numbers().e
            n = public_key.public_numbers().n
        else:
            raise UserError(_("Unsupported asymmetric cryptography algorithm '%s'. Currently supported: EC, RSA.", type(public_key)))

        return (
            _get_formatted_value(_int_to_bytes(e), formatting=formatting),
            _get_formatted_value(_int_to_bytes(n), formatting=formatting)
        )

    @api.model
    def _generate_ec_private_key(self, company, name='id_ec', curve='SECP256R1'):

        if curve not in STR_TO_CURVE:
            raise UserError(f"Unsupported curve algorithm '{curve}'. Currently supported: SECP256R1.")

        private_key = ec.generate_private_key(STR_TO_CURVE[curve])

        return self.env['certificate.key'].create({
            'name': name,
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())),
            'company_id': company.id,
        })

    @api.model
    def _generate_rsa_private_key(self, company, name='id_rsa', public_exponent=65537, key_size=2048):

        private_key = rsa.generate_private_key(
            public_exponent=public_exponent,
            key_size=key_size
        )

        return self.env['certificate.key'].create({
            'name': name,
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())),
            'company_id': company.id,
        })
