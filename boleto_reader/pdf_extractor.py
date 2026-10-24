"""Localiza linhas digitáveis no texto de PDFs e as decodifica."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pymupdf

from .linha_digitavel import LinhaDigitavelInvalida, ResultadoBoleto, decodificar, somente_digitos

logger = logging.getLogger(__name__)

# Formatos impressos mais comuns:
#   bancário:     00190.50095 40144.816069 06809.350314 3 37370000000100
#   arrecadação:  83620000000-5 66780048100-0 ... (ou blocos de 12 dígitos)
_PADRAO_BANCARIO = re.compile(
    r"\d{5}[.\s]?\d{5}\s*\d{5}[.\s]?\d{6}\s*\d{5}[.\s]?\d{6}\s*\d\s*\d{14}"
)
_PADRAO_ARRECADACAO = re.compile(r"8\d{10}[-\s]?\d(?:\s*\d{11}[-\s]?\d){3}")
_PADRAO_CORRIDO = re.compile(r"(?<!\d)(?:\d{47}|8\d{47})(?!\d)")


@dataclass
class ResultadoArquivo:
    arquivo: str
    boletos: list[ResultadoBoleto] = field(default_factory=list)
    erro: str | None = None

    def to_dict(self) -> dict:
        return {
            "arquivo": self.arquivo,
            "erro": self.erro,
            "boletos": [b.to_dict() for b in self.boletos],
        }


def extrair_texto(caminho_pdf: Path) -> str:
    with pymupdf.open(caminho_pdf) as doc:
        return "\n".join(pagina.get_text() for pagina in doc)


def encontrar_linhas(texto: str) -> list[str]:
    """Retorna as linhas digitáveis encontradas (somente dígitos, sem duplicatas, em ordem)."""
    candidatas: list[str] = []
    for padrao in (_PADRAO_BANCARIO, _PADRAO_ARRECADACAO, _PADRAO_CORRIDO):
        candidatas += [somente_digitos(m.group()) for m in padrao.finditer(texto)]
    return list(dict.fromkeys(candidatas))


def processar_pdf(caminho_pdf: Path, referencia: date | None = None) -> ResultadoArquivo:
    resultado = ResultadoArquivo(arquivo=caminho_pdf.name)
    try:
        texto = extrair_texto(caminho_pdf)
    except Exception as exc:  # PDF corrompido, protegido etc.
        logger.warning("Falha ao ler %s: %s", caminho_pdf.name, exc)
        resultado.erro = f"Não foi possível ler o PDF: {exc}"
        return resultado

    for linha in encontrar_linhas(texto):
        try:
            resultado.boletos.append(decodificar(linha, referencia))
        except LinhaDigitavelInvalida:
            continue

    if not resultado.boletos:
        resultado.erro = "Nenhuma linha digitável encontrada (o PDF pode ser uma imagem escaneada)."
    return resultado


def processar_pasta(pasta: Path, referencia: date | None = None) -> list[ResultadoArquivo]:
    arquivos = sorted(p for p in pasta.iterdir() if p.suffix.lower() == ".pdf")
    logger.info("%d PDF(s) encontrados em %s", len(arquivos), pasta)
    return [processar_pdf(p, referencia) for p in arquivos]
