# PrecisionClick (GUI)

Um autoclicker avançado e moderno com interface gráfica (PyQt6), suporte a sequências de macros, hotkeys globais e retículos de alvo.

## Funcionalidades

- **Interface Gráfica Moderna**: Design limpo e intuitivo baseado no tema "Catppuccin-like" com estilo Fusion.
- **Dois Modos de Operação**:
    - **Simples**: Repete cliques em um intervalo definido, opcionalmente em uma coordenada fixa.
    - **Sequência de Macros**: Crie uma lista de múltiplos pontos de clique com intervalos e botões diferentes para cada passo.
- **Hotkeys Globais Customizáveis**:
    - **Início/Pausa**: Configure qualquer tecla para iniciar (`[` por padrão) ou parar (`]` por padrão) a execução.
    - **Captura Rápida**: Pressione `P` enquanto passa o mouse sobre um local para capturar as coordenadas automaticamente.
- **Variância de Tempo**: Adicione um fator de aleatoriedade (+/- segundos) aos intervalos para simular comportamento humano e evitar detecção.
- **Retículos de Alvo**: Visualize exatamente onde os cliques ocorrerão com indicadores visuais semi-transparentes na tela.
- **Configurações de Clique**: Suporte para botões Esquerdo, Direito e do Meio.
- **Limite de Cliques**: Escolha entre cliques infinitos ou pare após atingir uma meta específica.
- **Feedback em Tempo Real**: Status da execução e contador de cliques visíveis na interface.

## Pré-requisitos

Este projeto utiliza o [uv](https://github.com/astral-sh/uv) para gerenciamento de dependências e ambiente virtual de alto desempenho.

## Instalação

```powershell
uv sync
```

## Como Usar

1. **Execute o programa**:
   ```powershell
   uv run python autoclick.py
   ```
2. **Configure o modo**: Escolha entre "Simple Repeating" ou "Macro Sequence".
3. **Capture coordenadas**:
    - No modo Simples: Marque "Fixed Coordinates" e pressione `P` sobre o alvo.
    - No modo Sequência: Pressione `P` repetidamente sobre diferentes pontos para adicioná-los à lista.
4. **Ajuste os intervalos**: Defina o tempo de espera e a variância desejada.
5. **Controle**:
    - Clique em **START EXECUTION** ou use a hotkey configurada (padrão `[`).
    - Clique em **STOP EXECUTION** ou use a hotkey configurada (padrão `]`).

## Tecnologias Utilizadas

- **PyQt6**: Interface gráfica robusta e responsiva.
- **PyAutoGUI**: Simulação precisa de eventos de mouse.
- **Keyboard**: Hook de teclado global para controle total.
- **UV**: Gestão moderna de pacotes Python.
