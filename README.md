
<img width="256" height="256" alt="icon" src="https://github.com/user-attachments/assets/32fc5a8d-00d2-4c3a-b24d-28f2115e0ac8" />

# PrecisionClick (GUI)

![PrecisionClick Interface](screenshot.png)

Um autoclicker avançado, moderno e premium com interface gráfica (PyQt6), suporte a sequências de macros, gravação interativa de cliques na tela, temas de cores customizados, hotkeys globais e retículos de alvo.

## Funcionalidades Premium

- **Interface Lateral Premium**: Layout elegante com uma barra de navegação à esquerda, painel de status global persistente, contador de cliques ativo e assinatura integrada.
- **Dois Modos de Operação**:
    - **Simples**: Repete cliques em um intervalo definido, opcionalmente em uma coordenada fixa.
    - **Sequência de Macros**: Crie e gerencie uma lista de múltiplos pontos de clique com intervalos, tipos de botões e variâncias individuais.
- **Gravação Interativa de Cliques (🎙️ Gravar Cliques)**:
    - Minimize o aplicativo com um clique e grave seus passos clicando diretamente na tela.
    - Pressione **ESC** para encerrar e retornar ao aplicativo com todos os passos adicionados automaticamente.
- **Rastreador de Posição em Tempo Real**: Veja a coordenada `X` e `Y` exata do seu cursor na aba de configurações atualizada de 50 em 50 milissegundos.
- **Personalização de Cores (Dynamic Themes)**:
    - Escolha entre 5 lindos temas de destaque baseados no Catppuccin: **Blue**, **Jade Green**, **Flamingo Pink**, **Amber Orange**, e **Royal Purple**.
- **Design de Botões Sofisticados**: Botões de início e parada com bordas brilhantes e cores desaturadas que se integram perfeitamente ao tema escuro premium.
- **Hotkeys Globais Customizáveis**:
    - **Início**: Configure uma tecla personalizada para iniciar a execução.
    - **Parada**: Configure uma tecla personalizada para parar a execução.
    - **Tecla de Captura**: Escolha qual tecla usar para capturar coordenadas enquanto passa o mouse na tela (padrão `P`).
- **Variância de Tempo**: Fator de aleatoriedade (+/- segundos) aos intervalos para simular comportamento humano real.
- **Retículos de Alvo**: Indicadores visuais semi-transparentes na tela mostrando onde os cliques ocorrerão.
- **Salvar/Carregar Perfis**: Exporte e importe suas listas de sequências de macros em formato JSON.

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
2. **Navegue pelas abas**: Use a barra lateral para alternar entre "Simple Repeating", "Macro Sequence", e "Hotkeys & Settings".
3. **Capture coordenadas**:
    - **Modo Manual**: Ative a coordenada fixa ou use a tabela e aperte a tecla de captura (padrão `P`) sobre o alvo.
    - **Modo Gravação (Macro)**: Clique em `🎙️ Record Clicks`, clique livremente na tela para registrar as coordenadas de clique, e aperte `ESC` para salvar.
4. **Altere o visual**: Vá na aba de configurações e mude o dropdown "Accent Color Theme" para alterar a cor do tema dinamicamente.
5. **Controle**:
    - Clique em **START EXECUTION** (ou use a hotkey configurada).
    - Clique em **STOP EXECUTION** (ou use a hotkey configurada).

## Tecnologias Utilizadas

- **PyQt6**: Interface gráfica robusta, moderna e responsiva.
- **PyAutoGUI**: Simulação precisa de eventos de mouse e suporte a clique duplo.
- **Keyboard**: Hook de teclado global para controle total de atalhos.
- **UV**: Gestão moderna de pacotes Python.

---
*Made by Vagner L.*
