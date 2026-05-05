# Autoclick Dinâmico (GUI)

Um autoclicker moderno com interface gráfica (PyQt6), hotkeys globais e suporte a limites de cliques.

## Funcionalidades

- **Interface Gráfica**: Configure tudo facilmente em uma janela intuitiva.
- **Início/Pausa via Teclado**: Use `F6` para começar e `F7` para parar instantaneamente, mesmo fora da janela.
- **Modos de Clique**: Escolha entre cliques infinitos ou uma quantidade específica.
- **Intervalo Personalizável**: Defina o tempo de espera entre cada clique (mínimo de 1ms).
- **Feedback em Tempo Real**: Visualize o status e o contador de cliques na interface.
- **Modo Dark/Light**: Interface limpa baseada no estilo Fusion do Qt.

## Pré-requisitos

Este projeto utiliza o [uv](https://github.com/astral-sh/uv) para gerenciamento de dependências e ambiente virtual.

## Instalação

```powershell
uv sync
```

## Como Usar

1. Execute o programa:
   ```powershell
   uv run python autoclick.py
   ```
2. Configure o intervalo e o limite de cliques na janela.
3. Clique em **Start** ou pressione **F6** para começar a clicar.
4. Clique em **Stop** ou pressione **F7** para pausar a qualquer momento.
5. Feche a janela para encerrar o programa.

## Tecnologias Utilizadas

- **PyQt6**: Para a interface gráfica moderna.
- **PyAutoGUI**: Para simulação dos cliques do mouse.
- **Keyboard**: Para detecção de teclas de atalho globais.
- **UV**: Para gestão ágil de pacotes Python.
