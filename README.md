# Sistema de Caixa — Lanchonete

Sistema de PDV (frente de caixa) para lanchonete: registra vendas com produto,
quantidade, valor, horário e vendedor; controla abertura e fechamento de caixa;
gera uma planilha Excel no fechamento; e guarda tudo em banco de dados para
consulta dos dias anteriores.

Feito para rodar no computador do balcão: **sem servidor, sem internet, sem instalação de banco**.

---

## Como rodar

```bash
# 1. Instalar a única dependência externa
pip install -r requirements.txt

# 2. (opcional) Popular com 7 dias de movimento para testar
python dados_exemplo.py

# 3. Abrir o sistema
python app.py
```

Requer **Python 3.10+**. O Tkinter já vem com o Python no Windows e no macOS;
no Linux pode ser preciso instalar à parte:

```bash
sudo apt install python3-tk
```

Na primeira execução o banco `dados/caixa.db` é criado sozinho, junto com um
cardápio inicial de exemplo e o funcionário "Gerente".

---

## Como o dia funciona no sistema

1. **Abrir caixa** — o funcionário informa quem está abrindo e o troco inicial da gaveta.
2. **Vender** — busca o produto digitando, `Enter` joga na comanda, `F2` finaliza.
   Cada venda grava horário, vendedor, forma de pagamento e todos os itens.
3. **Fechar caixa** — o sistema mostra o total vendido, quanto deveria ter na gaveta,
   e o funcionário informa quanto contou. A diferença fica registrada.
4. **Planilha** — no fechamento é gerado um `.xlsx` em `relatorios/`.
5. **Histórico** — dias fechados ficam disponíveis para consulta e para reabrir a planilha.

### Atalhos de teclado

| Tecla | Ação |
|---|---|
| `Enter` (na busca) | adiciona o produto à comanda |
| `Delete` | remove o item selecionado da comanda |
| `F2` | finaliza a venda |
| `F5` / `F8` / `F9` | Vender / Caixa do dia / Histórico |

---

## A planilha do fechamento

Quatro abas:

| Aba | Conteúdo |
|---|---|
| **Resumo** | dados do caixa, total vendido, ticket médio, formas de pagamento e conferência da gaveta |
| **Vendas do Dia** | uma linha por produto vendido: nº da venda, hora, vendedor, produto, qtd, valor unitário, subtotal, pagamento |
| **Por Produto** | consolidado: quanto saiu de cada item e quanto rendeu |
| **Por Funcionário** | quanto cada atendente vendeu e o % que representa do dia |

Os totais são gravados como **fórmulas** (`=SUM`, `=IFERROR`), não como números
prontos — o gerente pode filtrar ou corrigir uma linha e a planilha recalcula.

---

## Estrutura

```
caixa-lanchonete/
├── app.py                  # ponto de entrada
├── dados_exemplo.py        # gera movimento fictício para testes
├── requirements.txt
├── core/                   # regra de negócio e dados (não conhece a interface)
│   ├── moeda.py            # valores em centavos, parsing e formatação
│   ├── db.py               # conexão e esquema SQLite
│   ├── repositorio.py      # todo o SQL do projeto
│   ├── servicos.py         # abrir caixa, vender, cancelar, fechar
│   └── planilha.py         # geração do .xlsx
├── ui/                     # interface Tkinter
│   ├── estilo.py           # tema, cores e fontes
│   ├── componentes.py      # widgets e diálogos reutilizáveis
│   ├── janela.py           # janela principal e navegação
│   ├── tela_pdv.py         # frente de caixa
│   ├── tela_fechamento.py  # abertura e fechamento
│   ├── tela_historico.py   # consulta de dias anteriores
│   ├── tela_produtos.py    # cardápio
│   └── tela_equipe.py      # funcionários
├── testes/test_core.py     # 15 testes das regras de negócio
├── dados/                  # banco SQLite (criado na 1ª execução)
└── relatorios/             # planilhas geradas nos fechamentos
```

A interface nunca escreve SQL: ela chama `servicos`, que chama `repositorio`.
Por isso dá para testar todas as regras sem abrir janela nenhuma.

---

## Banco de dados

```
funcionarios ──┬─< caixas >─┬── vendas ──< itens_venda >── produtos
               └────────────┘
```

| Tabela | Guarda |
|---|---|
| `funcionarios` | quem vende e quem abre/fecha o caixa |
| `produtos` | cardápio com preço em centavos |
| `caixas` | abertura, fechamento, valores conferidos e caminho da planilha |
| `vendas` | horário, vendedor, forma de pagamento, total, flag de cancelamento |
| `itens_venda` | produto, quantidade, preço unitário e subtotal de cada item |

---

## Decisões técnicas

**Dinheiro em centavos (`INTEGER`), nunca `float`.**
`0.1 + 0.2 != 0.3` em ponto flutuante; num fechamento de caixa isso vira
divergência de gaveta. Toda conversão passa por `core/moeda.py`, que aceita os
formatos que o funcionário realmente digita (`12,50`, `12.50`, `R$ 1.234,56`).

**Um caixa aberto por vez, garantido pelo banco.**
Um índice único parcial (`WHERE status = 'ABERTO'`) impede dois caixas abertos
simultaneamente — a regra não depende de o código lembrar de verificar.

**Itens guardam uma fotografia do produto.**
`nome_produto` e `preco_unit_centavos` são copiados no momento da venda. Se o
preço do X-Burger mudar amanhã, o relatório de ontem continua correto.

**Nada é apagado.**
Produtos e funcionários são desativados (`ativo = 0`), nunca deletados, para não
quebrar o histórico. Vendas canceladas ficam marcadas com horário e motivo:
saem do total do dia, permanecem na auditoria.

**Venda e itens na mesma transação.**
Se a gravação de um item falhar, a venda inteira é revertida — nunca fica venda
órfã sem item.

**Fechamento separa gaveta de faturamento.**
O esperado na gaveta é `troco inicial + vendas em dinheiro`. Cartão, PIX e vale
entram no faturamento mas não na gaveta, então não contaminam a conferência.

---

## Testes

```bash
python -m unittest discover testes
```

Cobrem conversão e formatação de valores, bloqueio de caixa duplicado, recusa de
venda com caixa fechado, cálculo da diferença de gaveta, cancelamento de venda,
congelamento de preço no histórico, geração da planilha e consulta ao histórico.

---

## Gerar o executável (.exe)

Para rodar no computador do balcão sem precisar instalar Python:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name CaixaLanchonete app.py
```

O `.exe` fica em `dist/CaixaLanchonete.exe`. Copie só esse arquivo para a outra
máquina — `dados/` e `relatorios/` são criados automaticamente do lado dele na
primeira execução (`core/db.py` detecta quando está empacotado e usa a pasta do
`.exe`, não uma pasta temporária). Para atualizar o sistema, feche o programa,
rode o `pyinstaller` de novo e substitua o `.exe`; o banco em `dados/caixa.db`
não é tocado.

---

## Possíveis próximos passos

- Impressão de comprovante/cupom da venda
- Controle de estoque com baixa automática por item vendido
- Relatório consolidado por período (semana/mês) em uma planilha só
- Perfis de acesso: atendente não fecha caixa nem edita preços
