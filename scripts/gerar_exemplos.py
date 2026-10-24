"""Gera PDFs de boletos 100% fictícios em exemplos/ para demonstração e testes.

Banco 999 e o "Beneficiário Exemplo" não existem; os dígitos verificadores são
calculados para que as linhas sejam estruturalmente válidas.
"""

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from boleto_reader.linha_digitavel import gerar_linha_arrecadacao, gerar_linha_bancaria  # noqa: E402

PASTA = Path(__file__).resolve().parents[1] / "exemplos"


def criar_pdf(nome: str, linhas_texto: list[str]) -> None:
    doc = pymupdf.open()
    pagina = doc.new_page()
    y = 72
    for texto in linhas_texto:
        pagina.insert_text((50, y), texto, fontsize=11)
        y += 22
    doc.save(PASTA / nome)
    doc.close()


def main() -> None:
    PASTA.mkdir(exist_ok=True)

    linha1 = gerar_linha_bancaria("999", Decimal("1530.75"), date(2026, 11, 10), "1234567890123456789012345")
    criar_pdf("boleto_bancario_ficticio.pdf", [
        "BANCO EXEMPLO S.A. | 999-9",
        f"Linha digitavel: {linha1}",
        "Beneficiario: Empresa Ficticia de Servicos LTDA",
        "Vencimento: 10/11/2026     Valor: R$ 1.530,75",
    ])

    linha2 = gerar_linha_arrecadacao("2", Decimal("89.90"), "12345678901234567890123456789")
    criar_pdf("conta_consumo_ficticia.pdf", [
        "COMPANHIA DE SANEAMENTO EXEMPLO",
        "Conta referente a 10/2026",
        linha2,
        "Total a pagar: R$ 89,90",
    ])

    # Mesmo boleto com um dígito alterado: deve ser detectado como inválido.
    adulterada = linha1[:-1] + ("0" if linha1[-1] != "0" else "1")
    criar_pdf("boleto_com_digito_errado.pdf", ["BOLETO PARA TESTE DE VALIDACAO", adulterada])

    criar_pdf("documento_sem_boleto.pdf", ["Este PDF nao contem nenhum boleto."])
    print(f"PDFs gerados em {PASTA}")


if __name__ == "__main__":
    main()
