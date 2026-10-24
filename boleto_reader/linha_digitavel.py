"""
Decodificação e validação de linhas digitáveis de boletos brasileiros.

Suporta os dois layouts definidos pela FEBRABAN:

* **Boleto bancário / cobrança** — 47 dígitos (5 campos), DV dos campos por
  módulo 10 e DV geral do código de barras por módulo 11.
* **Arrecadação / convênio** (contas de consumo, tributos) — 48 dígitos
  (4 blocos de 11 + DV), começando por ``8``. O módulo do DV (10 ou 11)
  é definido pelo 3º dígito (identificador de valor).

Todas as regras aqui são públicas (especificação FEBRABAN); nenhuma regra de
negócio de empresa está implementada neste módulo.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import Decimal

# Datas-base do fator de vencimento. O fator chegou a 9999 em 21/02/2025 e
# reiniciou em 1000 no dia seguinte, então existem dois ciclos possíveis.
_BASE_CICLO_1 = date(1997, 10, 7)
_INICIO_CICLO_2 = date(2025, 2, 22)  # fator 1000 do novo ciclo


class LinhaDigitavelInvalida(ValueError):
    """A sequência não corresponde a nenhum layout de linha digitável."""


@dataclass
class ResultadoBoleto:
    tipo: str                    # "bancario" ou "arrecadacao"
    linha_digitavel: str         # apenas dígitos
    codigo_barras: str           # 44 dígitos
    valido: bool
    valor: Decimal | None
    vencimento: date | None = None
    banco: str | None = None
    segmento: str | None = None
    erros: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["valor"] = f"{self.valor:.2f}" if self.valor is not None else None
        d["vencimento"] = self.vencimento.isoformat() if self.vencimento else None
        return d


# ---------------------------------------------------------------------------
# Dígitos verificadores
# ---------------------------------------------------------------------------

def modulo10(numero: str) -> int:
    """DV módulo 10 (pesos 2,1 da direita para a esquerda)."""
    soma = 0
    peso = 2
    for digito in reversed(numero):
        produto = int(digito) * peso
        soma += produto // 10 + produto % 10
        peso = 1 if peso == 2 else 2
    return (10 - soma % 10) % 10


def _soma_modulo11(numero: str) -> int:
    soma = 0
    peso = 2
    for digito in reversed(numero):
        soma += int(digito) * peso
        peso = 2 if peso == 9 else peso + 1
    return soma


def modulo11_bancario(numero: str) -> int:
    """DV geral do código de barras de boleto bancário (resultado 0, 10 ou 11 vira 1)."""
    dv = 11 - _soma_modulo11(numero) % 11
    return 1 if dv in (0, 10, 11) else dv


def modulo11_arrecadacao(numero: str) -> int:
    """DV módulo 11 para arrecadação (resto 0 ou 1 → 0; resto 10 → 1)."""
    resto = _soma_modulo11(numero) % 11
    if resto in (0, 1):
        return 0
    if resto == 10:
        return 1
    return 11 - resto


# ---------------------------------------------------------------------------
# Fator de vencimento
# ---------------------------------------------------------------------------

def fator_para_data(fator: int, referencia: date | None = None) -> date | None:
    """Converte o fator de vencimento em data.

    Como o fator reiniciou em 2025, um mesmo número pode representar duas datas.
    Escolhemos a mais próxima da data de referência (hoje, por padrão).
    """
    if fator == 0:
        return None
    referencia = referencia or date.today()
    candidatas = [_BASE_CICLO_1 + timedelta(days=fator)]
    if fator >= 1000:
        candidatas.append(_INICIO_CICLO_2 + timedelta(days=fator - 1000))
    return min(candidatas, key=lambda d: abs((d - referencia).days))


def data_para_fator(vencimento: date) -> int:
    """Inverso de :func:`fator_para_data` (usado para gerar exemplos)."""
    if vencimento >= _INICIO_CICLO_2:
        return 1000 + (vencimento - _INICIO_CICLO_2).days
    return (vencimento - _BASE_CICLO_1).days


# ---------------------------------------------------------------------------
# Decodificação
# ---------------------------------------------------------------------------

def somente_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def decodificar(linha: str, referencia: date | None = None) -> ResultadoBoleto:
    """Detecta o layout e decodifica a linha digitável."""
    digitos = somente_digitos(linha)
    if len(digitos) == 47:
        return _decodificar_bancario(digitos, referencia)
    if len(digitos) == 48 and digitos[0] == "8":
        return _decodificar_arrecadacao(digitos)
    raise LinhaDigitavelInvalida(
        f"Esperados 47 dígitos (bancário) ou 48 iniciando em 8 (arrecadação); recebidos {len(digitos)}."
    )


def _decodificar_bancario(ld: str, referencia: date | None) -> ResultadoBoleto:
    campo1, dv1 = ld[0:9], int(ld[9])
    campo2, dv2 = ld[10:20], int(ld[20])
    campo3, dv3 = ld[21:31], int(ld[31])
    dv_geral = ld[32]
    fator_valor = ld[33:47]

    erros = []
    for nome, campo, dv in (("campo 1", campo1, dv1), ("campo 2", campo2, dv2), ("campo 3", campo3, dv3)):
        if modulo10(campo) != dv:
            erros.append(f"DV do {nome} inválido")

    banco_moeda = campo1[0:4]
    campo_livre = campo1[4:9] + campo2 + campo3
    codigo_barras = banco_moeda + dv_geral + fator_valor + campo_livre

    sem_dv = codigo_barras[:4] + codigo_barras[5:]
    if modulo11_bancario(sem_dv) != int(dv_geral):
        erros.append("DV geral do código de barras inválido")

    fator = int(fator_valor[0:4])
    valor = Decimal(int(fator_valor[4:])) / 100

    return ResultadoBoleto(
        tipo="bancario",
        linha_digitavel=ld,
        codigo_barras=codigo_barras,
        valido=not erros,
        valor=valor,
        vencimento=fator_para_data(fator, referencia),
        banco=banco_moeda[0:3],
        erros=erros,
    )


def _decodificar_arrecadacao(ld: str) -> ResultadoBoleto:
    blocos = [ld[i:i + 12] for i in range(0, 48, 12)]
    identificador_valor = ld[2]
    if identificador_valor in "67":
        calc_dv = modulo10
    elif identificador_valor in "89":
        calc_dv = modulo11_arrecadacao
    else:
        raise LinhaDigitavelInvalida(f"Identificador de valor desconhecido: {identificador_valor}")

    erros = [
        f"DV do bloco {i + 1} inválido"
        for i, bloco in enumerate(blocos)
        if calc_dv(bloco[:11]) != int(bloco[11])
    ]

    codigo_barras = "".join(b[:11] for b in blocos)
    sem_dv = codigo_barras[:3] + codigo_barras[4:]
    if calc_dv(sem_dv) != int(codigo_barras[3]):
        erros.append("DV geral do código de barras inválido")

    # 6 e 8 = valor efetivo em reais; 7 e 9 = quantidade de moeda/referência.
    valor = Decimal(int(codigo_barras[4:15])) / 100 if identificador_valor in "68" else None

    return ResultadoBoleto(
        tipo="arrecadacao",
        linha_digitavel=ld,
        codigo_barras=codigo_barras,
        valido=not erros,
        valor=valor,
        segmento=ld[1],
        erros=erros,
    )


# ---------------------------------------------------------------------------
# Geração (para testes e PDFs de exemplo com dados fictícios)
# ---------------------------------------------------------------------------

def gerar_linha_bancaria(banco: str, valor: Decimal, vencimento: date | None, campo_livre: str) -> str:
    """Monta uma linha digitável bancária válida a partir dos componentes."""
    if len(banco) != 3 or len(campo_livre) != 25:
        raise ValueError("banco deve ter 3 dígitos e campo_livre 25")
    fator = data_para_fator(vencimento) if vencimento else 0
    fator_valor = f"{fator:04d}{int(valor * 100):010d}"
    sem_dv = f"{banco}9{fator_valor}{campo_livre}"
    dv = modulo11_bancario(sem_dv)

    c1 = f"{banco}9{campo_livre[0:5]}"
    c2 = campo_livre[5:15]
    c3 = campo_livre[15:25]
    return (
        f"{c1[:5]}.{c1[5:]}{modulo10(c1)} "
        f"{c2[:5]}.{c2[5:]}{modulo10(c2)} "
        f"{c3[:5]}.{c3[5:]}{modulo10(c3)} "
        f"{dv} {fator_valor}"
    )


def gerar_linha_arrecadacao(segmento: str, valor: Decimal, resto: str) -> str:
    """Monta uma linha de arrecadação (identificador 6, módulo 10). ``resto`` tem 29 dígitos."""
    if len(resto) != 29:
        raise ValueError("resto deve ter 29 dígitos")
    sem_dv = f"8{segmento}6{int(valor * 100):011d}{resto}"
    dv = modulo10(sem_dv)
    barras = sem_dv[:3] + str(dv) + sem_dv[3:]
    blocos = [barras[i:i + 11] for i in range(0, 44, 11)]
    return " ".join(f"{b}-{modulo10(b)}" for b in blocos)
