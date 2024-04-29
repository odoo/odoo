import secrets

class TokenGenerator:

    def generate_token(length=32):
        return secrets.token_hex(length)

    def verify_token(token_to_check, expected_token):
        #Verifica que el token proporcionado sea correcto.

        # Utiliza una comparación constante en tiempo para prevenir ataques de timing
        return secrets.compare_digest(token_to_check, expected_token)


# Ejemplo de uso en otra parte del código:
# token = TokenGenerator.generate_token()
# is_valid = TokenGenerator.verify_token('token_del_usuario', token)

