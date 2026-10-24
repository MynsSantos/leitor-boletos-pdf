from datetime import date
from decimal import Decimal

import pymupdf
import pytest

from boleto_reader.linha_digitavel import (
    LinhaDigitavelInvalida,
    data_para_fator,
    decodificar,
    fator_para_data,
    gerar_linha_arrecadacao,
    gerar_linha_bancaria,
    modulo10,
)
from boleto_reader.pdf_extractor import encontrar_linhas, processar_pdf

# Exemplos públicos amplamente usados em documentação de boletos.
EXEMPLO_BANCARIO = "00190.50095 40144.816069 06809.350314 3 37370000000100"
EXEMPLO_ARRECADACAO = "836200000005 667800481000 180975657313 001589636081"


def test_modulo10_conhecido():
    assert modulo10("001905009") == 5


def test_decodifica_bancario_publico():
    r = decodificar(EXEMPLO_BANCARIO)
    assert r.valido and r.tipo == "bancario"
    assert r.banco == "001"
    assert r.valor == Decimal("1.00")
    assert len(r.codigo_barras) == 44


def test_decodifica_arrecadacao_publico():
    r = decodificar(EXEMPLO_ARRECADACAO)
    assert r.valido and r.tipo == "arrecadacao"
    assert r.valor == Decimal("66.78")


def test_detecta_digito_adulterado():
    adulterada = EXEMPLO_BANCARIO[:-1] + "9"
    r = decodificar(adulterada)
    assert not r.valido
    assert any("DV geral" in e for e in r.erros)


def test_tamanho_invalido():
    with pytest.raises(LinhaDigitavelInvalida):
        decodificar("123")


@pytest.mark.parametrize("vencimento", [date(2024, 12, 31), date(2025, 2, 21), date(2025, 2, 22), date(2027, 6, 1)])
def test_fator_ida_e_volta_entre_ciclos(vencimento):
    assert fator_para_data(data_para_fator(vencimento), referencia=vencimento) == vencimento


def test_gerador_bancario_ida_e_volta():
    linha = gerar_linha_bancaria("999", Decimal("1530.75"), date(2026, 11, 10), "1" * 25)
    r = decodificar(linha, referencia=date(2026, 10, 1))
    assert r.valido and r.valor == Decimal("1530.75") and r.vencimento == date(2026, 11, 10)


def test_gerador_arrecadacao_ida_e_volta():
    r = decodificar(gerar_linha_arrecadacao("2", Decimal("89.90"), "9" * 29))
    assert r.valido and r.valor == Decimal("89.90")


def test_encontra_linhas_em_texto_livre():
    texto = f"Pague até amanhã\nLinha: {EXEMPLO_BANCARIO}\nOutro: {EXEMPLO_ARRECADACAO}"
    assert len(encontrar_linhas(texto)) == 2


def test_processa_pdf(tmp_path):
    caminho = tmp_path / "boleto.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 72), f"Linha digitavel: {EXEMPLO_BANCARIO}")
    doc.save(caminho)
    doc.close()

    resultado = processar_pdf(caminho)
    assert resultado.erro is None
    assert resultado.boletos[0].valido


def test_pdf_sem_boleto(tmp_path):
    caminho = tmp_path / "vazio.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 72), "nada aqui")
    doc.save(caminho)
    doc.close()

    resultado = processar_pdf(caminho)
    assert resultado.boletos == [] and resultado.erro
