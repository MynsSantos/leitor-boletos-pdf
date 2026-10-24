"""CLI: python -m boleto_reader <arquivo.pdf | pasta> [--saida resultado.json]"""

import argparse
import json
import logging
from pathlib import Path

from .pdf_extractor import processar_pasta, processar_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrai e valida linhas digitáveis de boletos em PDF.")
    parser.add_argument("caminho", type=Path, help="Arquivo PDF ou pasta com PDFs")
    parser.add_argument("--saida", type=Path, help="Grava o resultado em JSON")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")

    if args.caminho.is_dir():
        resultados = processar_pasta(args.caminho)
    else:
        resultados = [processar_pdf(args.caminho)]

    saida = json.dumps([r.to_dict() for r in resultados], ensure_ascii=False, indent=2)
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(saida, encoding="utf-8")
    print(saida)


if __name__ == "__main__":
    main()
