# Leitor de Boletos em PDF

Extrai a **linha digitável** de boletos em PDF, converte para **código de barras (44 dígitos)** e **valida todos os dígitos verificadores** segundo a especificação pública da FEBRABAN — antes que um pagamento errado seja agendado.

> Projeto de portfólio inspirado em automações de contas a pagar que desenvolvi profissionalmente. Código escrito do zero, com dados 100% fictícios.

## O problema

Em rotinas financeiras, boletos chegam em PDF (e-mail, portais, processos internos) e alguém precisa digitar ou copiar a linha digitável no sistema de pagamento. Isso gera erros de digitação, boletos adulterados passam despercebidos e o valor/vencimento não é conferido.

## O que o projeto faz

- Lê PDFs (um arquivo ou uma pasta inteira) com **PyMuPDF**
- Encontra linhas digitáveis em diversos formatos impressos (com pontos, espaços, hífens ou corridas)
- Suporta os dois layouts:
  - **Bancário** (47 dígitos): DV dos 3 campos por módulo 10 + DV geral por módulo 11
  - **Arrecadação / convênio** (48 dígitos — contas de consumo e tributos): módulo 10 ou 11 conforme o identificador de valor
- Decodifica **banco, valor e vencimento**, incluindo o **reinício do fator de vencimento em 22/02/2025**
- Aponta exatamente qual dígito verificador falhou
- Saída em **JSON**, pronta para alimentar um robô RPA, uma API ou uma planilha

## Exemplo

```bash
pip install -r requirements.txt
python scripts/gerar_exemplos.py        # cria PDFs fictícios em exemplos/
python -m boleto_reader exemplos --saida output/resultado.json
```

```json
{
  "arquivo": "boleto_com_digito_errado.pdf",
  "boletos": [{
    "tipo": "bancario",
    "codigo_barras": "99993162600001530701234567890123456789012345",
    "valido": false,
    "valor": "1530.70",
    "vencimento": "2026-11-10",
    "erros": ["DV geral do código de barras inválido"]
  }]
}
```

Uso como biblioteca:

```python
from boleto_reader import decodificar

r = decodificar("00190.50095 40144.816069 06809.350314 3 37370000000100")
r.valido, r.banco, r.valor   # (True, '001', Decimal('1.00'))
```

## Estrutura

```
boleto_reader/
├── linha_digitavel.py   # regras FEBRABAN: módulos 10/11, fator de vencimento, decodificação
├── pdf_extractor.py     # leitura do PDF e localização das linhas por regex
└── __main__.py          # CLI
scripts/gerar_exemplos.py  # gera boletos fictícios estruturalmente válidos
tests/                     # pytest
```

## Testes

```bash
pytest
```

Cobrem exemplos públicos de documentação, detecção de dígito adulterado, virada do fator de vencimento entre ciclos e leitura de PDFs.

## Próximos passos

- Leitura do código de barras por imagem (PDFs escaneados) com `pyzbar`/OpenCV
- Conferência entre o valor impresso no boleto e o valor codificado na linha

## Tecnologias

Python 3.10+ · PyMuPDF · pytest · regex

---
Desenvolvido por **Yasmim Santos** · Licença MIT
