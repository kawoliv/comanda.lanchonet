"""
Hash e verificação de senha do Gerente.

Sem dependência externa: usa PBKDF2-HMAC-SHA256 da biblioteca padrão do
Python, com um salt aleatório por senha. O hash é guardado como
"salt_hex$hash_hex" na coluna `funcionarios.senha_hash`.
"""

import hashlib
import hmac
import secrets

_ITERACOES = 200_000


def gerar_hash_senha(senha: str) -> str:
    salt = secrets.token_hex(16)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"),
                                    bytes.fromhex(salt), _ITERACOES)
    return f"{salt}${derivado.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    if not senha or not hash_armazenado or "$" not in hash_armazenado:
        return False
    salt, hash_esperado = hash_armazenado.split("$", 1)
    derivado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"),
                                    bytes.fromhex(salt), _ITERACOES)
    return hmac.compare_digest(derivado.hex(), hash_esperado)
