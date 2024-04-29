# Controlador para la libreria de secrets en python y la generacion aleatoria de tokens.

import secrets

class TokenGenerator:

    
    def generate_token(length=32):
        #Genera un token aleatorio de longitud `length`.
        return secrets.token_hex(length)

    def verify_token(token_to_check, expected_token):
        #Verifica que el token proporcionado sea correcto.

        # Utiliza una comparación constante en tiempo para prevenir ataques de timing
        return secrets.compare_digest(token_to_check, expected_token)

# Ejemplo de uso en otra parte del código:
# token = TokenGenerator.generate_token()
# is_valid = TokenGenerator.verify_token('token_del_usuario', token)

