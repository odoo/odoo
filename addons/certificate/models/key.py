import base64
import contextlib

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
    'SECP256R1': ec.SECP256R1,
}


class Key(models.Model):
    _name = 'certificate.key'
    _description = 'Cryptographic Keys'
    _check_company_domain = models.check_company_domain_parent_of

    name = fields.Char(string='Name')
    content = fields.Binary(string='Key file', required=True)
    password = fields.Char(string='Private key password')
    pem_key = fields.Binary(string='Key bytes in PEM format', compute='_compute_pem_key', store=True, attachment=False)
    public = fields.Boolean(string='Public/Private key', compute='_compute_pem_key', store=True)
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
            pkey_content = base64.b64decode(key.content)
            pkey_password = key.password.encode('utf-8') if key.password else None

            # Try to load in the key in different format starting with DER then PEM. If none succeeded,
            # we raise an error.
            pkey = None
            with contextlib.suppress(ValueError):
                pkey = serialization.load_der_private_key(pkey_content, pkey_password)

            if not pkey:
                with contextlib.suppress(ValueError):
                    pkey = serialization.load_pem_private_key(pkey_content, pkey_password)

            if not pkey:
                raise UserError(_("The key could not be loaded."))

            try:
                key.pem_key = base64.b64encode(pkey.private_bytes(
                    encoding=Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
                key.public = False
            except AttributeError:
                pass
            if not key.pem_key:
                try:
                    key.pem_key = base64.b64encode(pkey.public_bytes(
                        encoding=Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    ))
                    key.public = True
                except AttributeError:
                    pass

            if not key.pem_key:
                raise UserError(_("The key could not be loaded."))

    # -------------------------------------------------------
    #                   Business Methods                    #
    # -------------------------------------------------------

    def _get_public_key_numbers_bytes(self, block=True):
        self.ensure_one()

        if self.public:
            public_key = serialization.load_pem_public_key(base64.b64decode(self.pem_key))
        else:
            public_key = serialization.load_pem_private_key(base64.b64decode(self.pem_key), None).public_key()

        if isinstance(public_key, ec.EllipticCurvePublicKey):
            e = public_key.public_numbers().x
            n = public_key.public_numbers().y
        elif isinstance(public_key, rsa.RSAPublicKey):
            e = public_key.public_numbers().e
            n = public_key.public_numbers().n
        else:
            raise UserError(_("Unsupported asymmetric cryptography algorithm. Currently supported: EC, RSA."))

        e = e.to_bytes((e.bit_length() + 7) // 8, 'big')
        n = n.to_bytes((n.bit_length() + 7) // 8, 'big')

        if block:
            return base64.encodebytes(e), base64.encodebytes(n)
        else:
            return base64.b64encode(e), base64.b64encode(n)

    def _get_public_key_bytes(self, encoding='der', block=True):
        self.ensure_one()

        if self.public:
            public_key = serialization.load_pem_public_key(base64.b64decode(self.pem_key))
        else:
            public_key = serialization.load_pem_private_key(base64.b64decode(self.pem_key), None).public_key()

        encoding = serialization.Encoding.DER if encoding == 'der' else serialization.Encoding.PEM
        if block:
            return base64.encodebytes(public_key.public_bytes(
                encoding=encoding,
                format=serialization.PublicFormat.SubjectPublicKeyInfo)
            )
        else:
            return base64.b64encode(public_key.public_bytes(
                encoding=encoding,
                format=serialization.PublicFormat.SubjectPublicKeyInfo)
            )

    def _decrypt(self, message, hashing_algorithm='sha256'):
        self.ensure_one()

        if not isinstance(message, bytes):
            message = message.encode('utf-8')

        if self.public:
            raise UserError(_("A private key is required to decrypt data."))
        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(_("Unsupported hashing algorithm. Currently supported: sha1 and sha256."))

        private_key = serialization.load_pem_private_key(base64.b64decode(self.pem_key), None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise UserError(_("Unsupported asymmetric cryptography algorithm. Currently supported: RSA."))

        return private_key.decrypt(
            message,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=STR_TO_HASH[hashing_algorithm]),
                algorithm=STR_TO_HASH[hashing_algorithm],
                label=None
            )
        )

    def _sign(self, message, hashing_algorithm='sha256', block=True):
        """ Return the base64 encoded signature of message. """
        self.ensure_one()

        if self.public:
            raise UserError(_("Make sure to use a private key to sign documents."))

        return self._sign_with_key(message, self.pem_key, pwd=None, hashing_algorithm=hashing_algorithm, block=block)

    @api.model
    def _sign_with_key(self, message, pem_key, pwd=None, hashing_algorithm='sha256', block=True):
        """ Return the base64 encoded signature of message. """

        if not isinstance(message, bytes):
            message = message.encode('utf-8')

        if hashing_algorithm not in STR_TO_HASH:
            raise UserError(_("Unsupported hashing algorithm. Currently supported: sha1 and sha256."))

        private_key = serialization.load_pem_private_key(base64.b64decode(pem_key), pwd)

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
            raise UserError(_("Unsupported asymmetric cryptography algorithm. Currently supported: EC and RSA."))

        if block:
            return base64.encodebytes(signature)
        else:
            return base64.b64encode(signature)

    @api.model
    def _generate_ec_private_key(self, name='id_ec', curve='SECP256R1'):

        if curve not in STR_TO_CURVE:
            raise UserError(_("Unsupported curve algorithm. Currently supported: SECP256R1."))

        private_key = ec.generate_private_key(STR_TO_CURVE[curve])

        return self.env['certificate.key'].create({
            'name': name,
            'content': base64.b64encode(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption())),
        })

    @api.model
    def _generate_rsa_private_key(self, name='id_rsa', public_exponent=65537, key_size=2048):

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
        })
