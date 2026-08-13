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
        ''' Compute and return the message's signature.

        :param str|bytes message: The message to sign
        :param optional,default='sha256' hashing_algorithm: The digest algorithm to use. Currently, only 'sha1' and 'sha256' are available.
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted signature bytes of the message
        :rtype: bytes
        '''
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
        ''' Get the public key's public numbers bytes.

        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: A tuple containing formatted public number bytes of the public key
        :rtype: tuple(bytes,bytes)
        '''
        self.ensure_one()

        return self._numbers_public_key_bytes_with_key(
            self._get_public_key_bytes(encoding='PEM'),
            formatting=formatting,
        )

    def _get_public_key_bytes(self, encoding='der', formatting='encodebytes'):
        ''' Get the public key bytes.

        :param optional,default='der' encoding: The formatting of the returned bytes
            - 'der' returns DER public key bytes
            - other returns PEM public key bytes
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted public key bytes in the corresponding format
        :rtype: bytes
        '''
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
        ''' Decrypt the given message using the provided digest.

        :param str|bytes message: The message to encode
        :param optional,default='sha256' hashing_algorithm: The digest algorithm to use. Currently, only 'sha1' and 'sha256' are available.
        :return: The decrypted text
        :rtype: str
        '''
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
        ).decode()

    @api.model
    def _sign_with_key(self, message, pem_key, pwd=None, hashing_algorithm='sha256', formatting='encodebytes'):
        ''' Compute and return the message's signature for a given private key.

        :param str|bytes message: The message to sign
        :param str|bytes pem_key: A base64 encoded private key in the PEM format
        :param str|bytes pwd: A password to decrypt the PEM key
        :param optional,default='sha1' hashing_algorithm: The digest algorithm to use. Currently, only 'sha1' and 'sha256' are available.
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: The formatted signature bytes of the message
        :rtype: bytes
        '''

        if not isinstance(message, bytes):
            message = message.encode('utf-8')
        if not isinstance(pem_key, bytes):
            pem_key = pem_key.encode('utf-8')
        if pwd and not isinstance(pwd, bytes):
            pwd = pwd.encode('utf-8')

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
        ''' Get the given public key's public numbers bytes.

        :param str|bytes pem_key: A base64 encoded public key in the PEM format
        :param optional,default='encodebytes' formatting: The formatting of the returned bytes
            - 'encodebytes' returns a base64-encoded block of 76 characters lines
            - 'base64' returns the raw base64-encoded data
            - other returns non-encoded data
        :return: A tuple containing the formatted public number bytes of the public key
        :rtype: tuple(bytes,bytes)
        '''
        if not isinstance(pem_key, bytes):
            pem_key = pem_key.encode('utf-8')

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
        ''' Generate an elliptic curve private key.

        :param res.company company: A company record
        :param str,optional,default='id_ec' name: The name of the newly created key.
        :param optional,default='SECP256R1' curve: The type of elliptic curve algorithm. Currently, only SECP256R1 is supported.
        :return: A certificate.key record
        :rtype: certificate.key
        '''
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
        ''' Generate an RSA private key.

        :param res.company company: A company record
        :param str,optional,default='id_rsa' name: The name of the newly created key.
        :param int,optional,default=65537 public_exponent: The public exponent of the new key: either 65537 or 3 (for legacy purposes)
        :param int,optional,default=2048 key_size: The length of the modulus in bits; it is strongly recommended to be at least 2048 and must not be less than 512
        :return: A certificate.key record
        :rtype: certificate.key
        '''
        if (public_exponent not in [65537, 3]):
            raise UserError(_("The public exponent should be 65537 (or 3 for legacy purposes)."))
        if key_size < 512:
            raise UserError(_("The key size should be at least 512 bytes."))

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
