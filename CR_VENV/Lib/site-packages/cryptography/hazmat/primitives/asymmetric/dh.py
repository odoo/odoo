# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.


import abc
import typing

from cryptography import utils
from cryptography.hazmat.backends import _get_backend
from cryptography.hazmat.primitives import serialization


_MIN_MODULUS_SIZE = 512


def generate_parameters(generator, key_size, backend=None) -> "DHParameters":
    backend = _get_backend(backend)
    return backend.generate_dh_parameters(generator, key_size)


class DHParameterNumbers(object):
    def __init__(self, p: int, g: int, q: typing.Optional[int] = None):
        if not isinstance(p, int) or not isinstance(g, int):
            raise TypeError("p and g must be integers")
        if q is not None and not isinstance(q, int):
            raise TypeError("q must be integer or None")

        if g < 2:
            raise ValueError("DH generator must be 2 or greater")

        if p.bit_length() < _MIN_MODULUS_SIZE:
            raise ValueError(
                "p (modulus) must be at least {}-bit".format(_MIN_MODULUS_SIZE)
            )

        self._p = p
        self._g = g
        self._q = q

    def __eq__(self, other):
        if not isinstance(other, DHParameterNumbers):
            return NotImplemented

        return (
            self._p == other._p and self._g == other._g and self._q == other._q
        )

    def __ne__(self, other):
        return not self == other

    def parameters(self, backend=None):
        backend = _get_backend(backend)
        return backend.load_dh_parameter_numbers(self)

    p = utils.read_only_property("_p")
    g = utils.read_only_property("_g")
    q = utils.read_only_property("_q")


class DHPublicNumbers(object):
    def __init__(self, y, parameter_numbers: DHParameterNumbers):
        if not isinstance(y, int):
            raise TypeError("y must be an integer.")

        if not isinstance(parameter_numbers, DHParameterNumbers):
            raise TypeError(
                "parameters must be an instance of DHParameterNumbers."
            )

        self._y = y
        self._parameter_numbers = parameter_numbers

    def __eq__(self, other):
        if not isinstance(other, DHPublicNumbers):
            return NotImplemented

        return (
            self._y == other._y
            and self._parameter_numbers == other._parameter_numbers
        )

    def __ne__(self, other):
        return not self == other

    def public_key(self, backend=None) -> "DHPublicKey":
        backend = _get_backend(backend)
        return backend.load_dh_public_numbers(self)

    y = utils.read_only_property("_y")
    parameter_numbers = utils.read_only_property("_parameter_numbers")


class DHPrivateNumbers(object):
    def __init__(self, x, public_numbers: DHPublicNumbers):
        if not isinstance(x, int):
            raise TypeError("x must be an integer.")

        if not isinstance(public_numbers, DHPublicNumbers):
            raise TypeError(
                "public_numbers must be an instance of " "DHPublicNumbers."
            )

        self._x = x
        self._public_numbers = public_numbers

    def __eq__(self, other):
        if not isinstance(other, DHPrivateNumbers):
            return NotImplemented

        return (
            self._x == other._x
            and self._public_numbers == other._public_numbers
        )

    def __ne__(self, other):
        return not self == other

    def private_key(self, backend=None) -> "DHPrivateKey":
        backend = _get_backend(backend)
        return backend.load_dh_private_numbers(self)

    public_numbers = utils.read_only_property("_public_numbers")
    x = utils.read_only_property("_x")


class DHParameters(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def generate_private_key(self) -> "DHPrivateKey":
        """
        Generates and returns a DHPrivateKey.
        """

    @abc.abstractmethod
    def parameter_bytes(
        self,
        encoding: "serialization.Encoding",
        format: "serialization.ParameterFormat",
    ) -> bytes:
        """
        Returns the parameters serialized as bytes.
        """

    @abc.abstractmethod
    def parameter_numbers(self) -> DHParameterNumbers:
        """
        Returns a DHParameterNumbers.
        """


DHParametersWithSerialization = DHParameters


class DHPublicKey(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def key_size(self) -> int:
        """
        The bit length of the prime modulus.
        """

    @abc.abstractmethod
    def parameters(self) -> DHParameters:
        """
        The DHParameters object associated with this public key.
        """

    @abc.abstractmethod
    def public_numbers(self) -> DHPublicNumbers:
        """
        Returns a DHPublicNumbers.
        """

    @abc.abstractmethod
    def public_bytes(
        self,
        encoding: "serialization.Encoding",
        format: "serialization.PublicFormat",
    ) -> bytes:
        """
        Returns the key serialized as bytes.
        """


DHPublicKeyWithSerialization = DHPublicKey


class DHPrivateKey(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def key_size(self) -> int:
        """
        The bit length of the prime modulus.
        """

    @abc.abstractmethod
    def public_key(self) -> DHPublicKey:
        """
        The DHPublicKey associated with this private key.
        """

    @abc.abstractmethod
    def parameters(self) -> DHParameters:
        """
        The DHParameters object associated with this private key.
        """

    @abc.abstractmethod
    def exchange(self, peer_public_key: DHPublicKey) -> bytes:
        """
        Given peer's DHPublicKey, carry out the key exchange and
        return shared key as bytes.
        """

    @abc.abstractmethod
    def private_numbers(self) -> DHPrivateNumbers:
        """
        Returns a DHPrivateNumbers.
        """

    @abc.abstractmethod
    def private_bytes(
        self,
        encoding: "serialization.Encoding",
        format: "serialization.PrivateFormat",
        encryption_algorithm: "serialization.KeySerializationEncryption",
    ) -> bytes:
        """
        Returns the key serialized as bytes.
        """


DHPrivateKeyWithSerialization = DHPrivateKey
