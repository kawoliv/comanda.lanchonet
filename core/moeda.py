"""
Utilitários para valores monetários.

REGRA DO PROJETO: todo dinheiro é guardado como INTEGER de centavos.
Float com dinheiro dá erro de arredondamento (0.1 + 0.2 != 0.3) e, num caixa,
esse erro vira divergência no fechamento. Convertemos para float apenas na
hora de escrever na planilha.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


class ValorInvalido(ValueError):
    """Levantado quando o texto informado não representa um valor monetário."""


def para_centavos(valor) -> int:
    """
    Converte texto ou número para centavos.

    Aceita os formatos que o funcionário costuma digitar:
    "12,50" · "12.50" · "R$ 12,50" · "1.234,56" · 12.5 · 1250 (int já em reais).
    """
    if valor is None or isinstance(valor, bool):
        raise ValorInvalido("Informe um valor.")

    if isinstance(valor, (int, float, Decimal)):
        decimal = Decimal(str(valor))
    else:
        texto = str(valor).strip()
        if not texto:
            raise ValorInvalido("Informe um valor.")

        texto = texto.replace("R$", "").replace(" ", "").replace("\u00a0", "")

        # "1.234,56" -> "1234.56"  |  "12,50" -> "12.50"
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")

        try:
            decimal = Decimal(texto)
        except InvalidOperation as erro:
            raise ValorInvalido(f'"{valor}" não é um valor válido.') from erro

    centavos = (decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(centavos)


def formatar(centavos: int) -> str:
    """1234567 -> 'R$ 12.345,67'"""
    centavos = int(centavos or 0)
    sinal = "-" if centavos < 0 else ""
    inteiro, resto = divmod(abs(centavos), 100)
    milhar = f"{inteiro:,}".replace(",", ".")
    return f"{sinal}R$ {milhar},{resto:02d}"


def para_reais(centavos: int) -> float:
    """Converte centavos para float. Use só na saída (planilha, gráfico)."""
    return int(centavos or 0) / 100
