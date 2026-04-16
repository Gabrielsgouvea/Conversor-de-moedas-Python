# -*- coding: utf-8 -*-

import wx
import wx.xrc
import gettext
import requests

_ = gettext.gettext

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

c_titulo_janela = u"Converte Moedas"

# Nomes exibidos nas combo boxes (ordem de exibição)
c_moedas = [
    "Real (BRL)",
    "Dólar (USD)",
    "Euro (EUR)",
    "Libra (GBP)",
    "Bitcoin em Dólar (BTC/USD)",
    "Ethereum em Dólar (ETH/USD)",
    "Yuan Chinês (CNY)",
]

# Códigos fiat usados pela API frankfurter.app (base BRL)
c_codigos_fiat = {
    "Real (BRL)":        "BRL",
    "Dólar (USD)":       "USD",
    "Euro (EUR)":        "EUR",
    "Libra (GBP)":       "GBP",
    "Yuan Chinês (CNY)": "CNY",
}

# IDs CoinGecko para cripto
c_codigos_cripto = {
    "Bitcoin em Dólar (BTC/USD)":  "bitcoin",
    "Ethereum em Dólar (ETH/USD)": "ethereum",
}

# URLs das APIs
c_url_fiat   = "https://api.frankfurter.app/latest?base=BRL&symbols=USD,EUR,GBP,CNY"
c_url_cripto = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=brl"

# Timeout de conexão em segundos
c_timeout = 5


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def fct_str_para_float(a_texto: str) -> float:
    """Converte string no formato moeda BR (vírgula decimal) para float."""
    v_texto_limpo = a_texto.replace(".", "").replace(",", ".")
    return float(v_texto_limpo)


def fct_float_para_str(a_valor: float) -> str:
    """Formata float para string no formato moeda BR (ex: 1.234,56)."""
    v_formatado = f"{a_valor:,.2f}"
    v_formatado = v_formatado.replace(",", "X").replace(".", ",").replace("X", ".")
    return v_formatado


def fct_buscar_cotacoes() -> dict:
    """
    Busca cotações em tempo real e retorna dict {nome_moeda: valor_em_brl}.
    Lança Exception se qualquer requisição falhar.
    """
    v_taxas = {"Real (BRL)": 1.0}

    # --- Fiat via frankfurter.app ---
    # Resposta: {"rates": {"USD": 0.1754, "EUR": 0.1612, ...}}
    # 1 BRL = X moeda  →  1 moeda = 1/X BRL
    v_resp_fiat = requests.get(c_url_fiat, timeout=c_timeout)
    v_resp_fiat.raise_for_status()
    v_rates = v_resp_fiat.json()["rates"]

    for v_nome, v_codigo in c_codigos_fiat.items():
        if v_codigo == "BRL":
            continue
        v_taxas[v_nome] = 1.0 / v_rates[v_codigo]

    # --- Cripto via CoinGecko ---
    # Resposta: {"bitcoin": {"brl": 350000}, "ethereum": {"brl": 18000}}
    v_resp_cripto = requests.get(c_url_cripto, timeout=c_timeout)
    v_resp_cripto.raise_for_status()
    v_precos = v_resp_cripto.json()

    for v_nome, v_id in c_codigos_cripto.items():
        v_taxas[v_nome] = v_precos[v_id]["brl"]

    return v_taxas


def fct_converter(a_valor: float, a_moeda_origem: str, a_moeda_destino: str,
                  a_taxas: dict) -> float:
    """Converte valor entre duas moedas usando BRL como pivô."""
    v_em_brl    = a_valor * a_taxas[a_moeda_origem]
    v_resultado = v_em_brl / a_taxas[a_moeda_destino]
    return v_resultado


# ---------------------------------------------------------------------------
# Classe principal
# ---------------------------------------------------------------------------

class fr_converte_moedas(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title=_(c_titulo_janela),
                          pos=wx.DefaultPosition, size=wx.DefaultSize,
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        self.SetSize(wx.Size(440, 290))

        # Fonte — precisa do wx.App já criado
        self._c_fonte_padrao = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                       wx.FONTWEIGHT_NORMAL, False, wx.EmptyString)

        # Controle interno para evitar loop no evento de texto
        self._v_editando = False

        # Cotações carregadas na inicialização
        self._v_taxas = {}
        self._fct_carregar_cotacoes()

        # ----------------------------------------------------------------
        # Layout raiz: 2 colunas
        # ----------------------------------------------------------------
        bs_separador = wx.GridSizer(0, 2, 0, 0)

        # ---- Coluna esquerda: moeda de origem ----
        bs_moeda_corrente = wx.BoxSizer(wx.VERTICAL)

        self.st_escolha_moeda_corrente = wx.StaticText(
            self, wx.ID_ANY, _(u"Escolha a moeda corrente:"))
        self.st_escolha_moeda_corrente.SetFont(self._c_fonte_padrao)
        bs_moeda_corrente.Add(self.st_escolha_moeda_corrente,
                              0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.cb_moeda_corrente = wx.ComboBox(
            self, wx.ID_ANY, choices=c_moedas, style=wx.CB_READONLY)
        self.cb_moeda_corrente.SetFont(self._c_fonte_padrao)
        self.cb_moeda_corrente.SetSelection(0)
        bs_moeda_corrente.Add(self.cb_moeda_corrente,
                              0, wx.ALIGN_CENTER | wx.ALL, 10)

        self.st_digitar_valor = wx.StaticText(
            self, wx.ID_ANY, _(u"Digite o valor da moeda corrente:"))
        self.st_digitar_valor.SetFont(self._c_fonte_padrao)
        bs_moeda_corrente.Add(self.st_digitar_valor,
                              0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        self.tx_digito_moeda_corrente = wx.TextCtrl(
            self, wx.ID_ANY, u"0,00", style=wx.TE_CENTER)
        self.tx_digito_moeda_corrente.SetMaxLength(15)
        self.tx_digito_moeda_corrente.SetFont(self._c_fonte_padrao)
        bs_moeda_corrente.Add(self.tx_digito_moeda_corrente,
                              0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        bs_separador.Add(bs_moeda_corrente, 1, wx.EXPAND, 5)

        # ---- Coluna direita: moeda de destino ----
        bs_moeda_convertida = wx.BoxSizer(wx.VERTICAL)

        self.st_moeda_convertida = wx.StaticText(
            self, wx.ID_ANY, _(u"Escolha a moeda convertida:"))
        self.st_moeda_convertida.SetFont(self._c_fonte_padrao)
        bs_moeda_convertida.Add(self.st_moeda_convertida,
                                0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        self.cb_moeda_converida = wx.ComboBox(
            self, wx.ID_ANY, choices=c_moedas, style=wx.CB_READONLY)
        self.cb_moeda_converida.SetFont(self._c_fonte_padrao)
        self.cb_moeda_converida.SetSelection(1)
        bs_moeda_convertida.Add(self.cb_moeda_converida,
                                0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        self.st_moeda_convertida_info = wx.StaticText(
            self, wx.ID_ANY, _(u"O valor convertido é:"))
        bs_moeda_convertida.Add(self.st_moeda_convertida_info,
                                0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        self.st_valor_convertido = wx.StaticText(self, wx.ID_ANY, u"0,00")
        self.st_valor_convertido.SetFont(self._c_fonte_padrao)
        bs_moeda_convertida.Add(self.st_valor_convertido,
                                0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 10)

        self.bt_converter = wx.Button(self, wx.ID_ANY, _(u"Converter"))
        self.bt_converter.SetFont(self._c_fonte_padrao)
        bs_moeda_convertida.Add(self.bt_converter,
                                0, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.bt_atualizar = wx.Button(self, wx.ID_ANY, _(u"Atualizar cotações"))
        self.bt_atualizar.SetFont(self._c_fonte_padrao)
        bs_moeda_convertida.Add(self.bt_atualizar,
                                0, wx.ALIGN_RIGHT | wx.ALL, 5)

        bs_separador.Add(bs_moeda_convertida, 1, wx.EXPAND, 5)

        self.SetSizer(bs_separador)
        self.Layout()
        self.Centre(wx.BOTH)

        # ---- Eventos ----
        self.tx_digito_moeda_corrente.Bind(wx.EVT_TEXT,  self.e_apenas_numeros)
        self.bt_converter.Bind(wx.EVT_BUTTON,            self.e_converter)
        self.bt_atualizar.Bind(wx.EVT_BUTTON,            self.e_atualizar_cotacoes)

    def __del__(self):
        pass

    # ----------------------------------------------------------------
    # Métodos internos
    # ----------------------------------------------------------------

    def _fct_carregar_cotacoes(self):
        """Busca cotações e armazena em self._v_taxas. Exibe erro se falhar."""
        try:
            self._v_taxas = fct_buscar_cotacoes()
        except Exception as v_erro:
            wx.MessageBox(
                _(u"Não foi possível buscar as cotações:\n") + str(v_erro),
                _(u"Erro de conexão"), wx.OK | wx.ICON_ERROR)
            self._v_taxas = {}

    # ----------------------------------------------------------------
    # Eventos
    # ----------------------------------------------------------------

    def e_apenas_numeros(self, event):
        """Permite apenas dígitos; formata como moeda BR ao digitar."""
        if self._v_editando:
            event.Skip()
            return

        self._v_editando = True

        v_ctrl            = self.tx_digito_moeda_corrente
        v_texto           = v_ctrl.GetValue()
        v_somente_digitos = "".join(c for c in v_texto if c.isdigit()) or "0"
        v_centavos        = int(v_somente_digitos)
        v_reais           = v_centavos / 100.0
        v_formatado       = fct_float_para_str(v_reais)

        v_ctrl.ChangeValue(v_formatado)
        v_ctrl.SetInsertionPointEnd()

        self._v_editando = False
        event.Skip()

    def e_converter(self, event):
        """Converte o valor e exibe em st_valor_convertido."""
        if not self._v_taxas:
            wx.MessageBox(_(u"Cotações não carregadas. Clique em 'Atualizar cotações'."),
                          _(u"Aviso"), wx.OK | wx.ICON_WARNING)
            return

        v_moeda_origem  = self.cb_moeda_corrente.GetValue()
        v_moeda_destino = self.cb_moeda_converida.GetValue()
        v_texto_valor   = self.tx_digito_moeda_corrente.GetValue()

        if not v_moeda_origem or not v_moeda_destino:
            wx.MessageBox(_(u"Selecione as duas moedas."),
                          _(u"Aviso"), wx.OK | wx.ICON_WARNING)
            return

        try:
            v_valor_float = fct_str_para_float(v_texto_valor)
        except ValueError:
            wx.MessageBox(_(u"Valor inválido. Use o formato: 1.234,56"),
                          _(u"Erro"), wx.OK | wx.ICON_ERROR)
            return

        v_resultado = fct_converter(v_valor_float, v_moeda_origem,
                                    v_moeda_destino, self._v_taxas)
        self.st_valor_convertido.SetLabel(fct_float_para_str(v_resultado))

        event.Skip()

    def e_atualizar_cotacoes(self, event):
        """Rebusca as cotações nas APIs."""
        self.bt_atualizar.SetLabel(_(u"Buscando..."))
        self.bt_atualizar.Disable()
        self.Update()

        self._fct_carregar_cotacoes()

        self.bt_atualizar.SetLabel(_(u"Atualizar cotações"))
        self.bt_atualizar.Enable()

        if self._v_taxas:
            wx.MessageBox(_(u"Cotações atualizadas com sucesso."),
                          _(u"OK"), wx.OK | wx.ICON_INFORMATION)
        event.Skip()

if __name__ == "__main__":
    app = wx.App()
    frame = fr_converte_moedas(None)
    frame.Show()
    app.MainLoop()