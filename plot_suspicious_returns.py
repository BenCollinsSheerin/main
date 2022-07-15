# coding=utf-8
"""
This code makes all figures of "They Still Haven't Told You" (2022)
        (https://ssrn.com/abstract=3998202, https://arxiv.org/abs/2201.00223)
    and all figures of "They Chose to Not Tell You" (2021)
        (https://ssrn.com/abstract=3894013, https://arxiv.org/abs/2107.12516)

Appropriately modified, this code also makes:
  + Figure 1 of "Strikingly Suspicious Overnight and Intraday Returns" (2020)
        (https://ssrn.com/abstract=3705017, https://arxiv.org/abs/2010.01727)
  + Figures 2 and 3 of "Celebrating Three Decades of Worldwide Stock Market Manipulation" (2019)
        (https://ssrn.com/abstract=3490879, https://arxiv.org/abs/1912.01708)
  + Figure 1 of "How to Increase Global Wealth Inequality for Fun and Profit" (2018)
        (https://ssrn.com/abstract=3282845, https://arxiv.org/abs/1811.04994)

We assume the user has a python 2.7 environment with matplotlib.

Before running, set INPUT_DATA_DIR and OUTPUT_PLOT_DIR to the local directories
in which you wish to store files with price data and output plots, respectively.

Bruce Knuteson (knuteson@mit.edu)
2022-01-01

Updates:
  2022-04-08  Adding plot_overnight_intraday_returns_dax(), which plots overnight/intraday returns for the constituents
                of Germany's DAX index.
"""
from datetime import datetime, timedelta
from math import sqrt, erf
import os
import random
import re
import requests
import urllib
from time import mktime, sleep

from matplotlib.dates import date2num, YearLocator
from matplotlib.pyplot import xlim, subplots, figure, gca, savefig, clf, hist, figtext, ylabel, xlabel, title

DATETIME_FORMAT = "%Y-%m-%d"
DEFAULT_START_DATE = datetime(1990, 1, 1)
DEFAULT_END_DATE = datetime(2021, 12, 31)
# ADJUST INPUT_DATA_DIR AND OUTPUT_PLOT_DIR AS NECESSARY FOR YOUR LOCAL ENVIRONMENT
# csv files with open and close prices will be downloaded to INPUT_DATA_DIR
INPUT_DATA_DIR = "."
# plots will be saved in OUTPUT_PLOT_DIR
OUTPUT_PLOT_DIR = "."


def symbol_details_dict():
    """
    Return a dict with a few pieces of useful information for the indices and individual stocks we consider.

    This information includes (where appropriate):
      + a formal(ish) and/or common name;
      + the home country; and
      + a start date, end date, and/or bad_data_dates (if manual analysis has identified specific problems).

    @rtype: dict[str, dict[str]]
    """
    return dict([
        # Indices shown in Figure 1 of "How to Increase Global Wealth Inequality for Fun and Profit" (2018)
        ("SPY", dict(name="S&P 500 SPDR ETF", country="United States", short_name="S&P 500")),
        ("^IXIC", dict(name="NASDAQ Composite", country="United States", short_name="NASDAQ")),
        ("XIU.TO", dict(name="iShares TSX 60 ETF", country="Canada", short_name="TSX 60")),
        ("^FCHI", dict(name="CAC 40", country="France")),
        ("^GDAXI", dict(name="DAX", country="Germany")),
        ("^N225", dict(name="Nikkei 225", country="Japan")),

        # Indices added in Figures 2 and 3 of "Celebrating Three Decades of Worldwide Stock Market Manipulation" (2019)
        ("ISFU.L", dict(name="iShares Core FTSE 100 ETF", country="United Kingdom", short_name="FTSE 100",
                        end_date=datetime(2018, 6, 20),  # last date data are available
                        bad_data_dates=[datetime(2001, 7, 16)]  # bad open price
                        )),
        ("^AEX", dict(name="AEX", country="Netherlands",
                      bad_data_dates=[datetime(1995, 12, 26)]  # bad prices
                      )),
        ("OBXEDNB.OL", dict(name="DNB OBX ETF", country="Norway", short_name="DNB OBX",
                            # open prices are zero from 2009-01-01 to 2009-05-06
                            start_date=datetime(2009, 5, 8),
                            bad_data_dates=[datetime(2009, 11, 12),  # zero open price
                                            datetime(2009, 11, 13),  # zero open price
                                            datetime(2013, 1, 4)  # bad close price
                                            ])),
        ("^TA125.TA", dict(name="TA-125", country="Israel",
                           # more than half of the TA-125 overnight returns are zero before 2007.
                           start_date=datetime(2007, 1, 8))),
        ("STW.AX", dict(name="SPDR S&P/ASX 200 Fund", country="Australia", short_name="ASX 200")),
        ("^NSEI", dict(name="NIFTY 50", country="India")),
        ("^BSESN", dict(name="S&P BSE SENSEX", country="India", short_name="SENSEX")),
        ("^HSI", dict(name="Hang Seng Index", country="Hong Kong", short_name="Hang Seng")),
        ("ES3.SI", dict(name="SPDR Straits Times Index ETF", country="Singapore", short_name="Straits Times")),
        ("000001.SS", dict(name="SSE Composite Index", country="China", short_name="SSE")),

        # Indices added in Figure 1 of "Strikingly Suspicious Overnight and Intraday Returns" (2020)
        ("IMIB.MI", dict(name="iShares FTSE MIB ETF", country="Italy", short_name="FTSE MIB")),
        ("^KS11", dict(name="KOSPI Composite Index", country="Korea", short_name="KOSPI")),
        ("^TWII", dict(name="TSEC Weighted Index", country="Taiwan", short_name="TSEC")),
        ("EWW", dict(name="iShares MSCI Mexico Capped ETF", country="Mexico", short_name="MSCI Mexico")),
        ("EWZ", dict(name="iShares MSCI Brazil Capped ETF", country="Brazil", short_name="MSCI Brazil")),

        # Index added in Figure 2 of "They Still Haven't Told You" (2022)
        ("^IBEX", dict(name="IBEX 35", country="Spain")),

        # Largest US companies, shown in Figure 2 of "They Chose to Not Tell You" (2021)
        ("AAPL", dict(name="Apple")),
        ("MSFT", dict(name="Microsoft")),
        ("AMZN", dict(name="Amazon")),
        ("GOOG", dict(name="Google")),
        ("FB", dict(name="Facebook")),
        ("TSLA", dict(name="Tesla")),
        ("BRK-B", dict(name="Berkshire Hathaway")),
        ("V", dict(name="Visa")),
        ("NVDA", dict(name="NVIDIA")),
        ("JPM", dict(name="JPMorgan Chase")),
        ("UNH", dict(name="UnitedHealth")),

        # Meme stocks, shown in Figure 6 of "They Still Haven't Told You" (2022)
        # and Figure 3 of "They Chose to Not Tell You" (2021)
        ("GME", dict(name="GameStop")),
        ("AMC", dict(name="AMC Entertainment", short_name="AMC")),

        # Evergrande, shown in Figure 7 of "They Still Haven't Told You" (2022)
        ("3333.HK", dict(name="China Evergrande Group", start_date=datetime(2010, 1, 1))),

        # The start of the list of companies in the US S&P 500, sorted alphabetically,
        # shown in Figure 3 of "They Still Haven't Told You" (2022).
        # Reference:  https://en.wikipedia.org/wiki/List_of_S&P_500_companies
        # See also:  https://markets.ft.com/data/indices/tearsheet/constituents?s=INX:IOM
        ("MMM", dict(name="3M")),
        ("AOS", dict(name="A O Smith")),
        ("ABT", dict(name="Abbott Laboratories")),
        ("ABBV", dict(name="Abbvie")),
        ("ABMD", dict(name="Abiomed")),
        ("ACN", dict(name="Accenture")),
        ("ATVI", dict(name="Activision Blizzard")),
        ("ADBE", dict(name="Adobe")),
        ("AAP", dict(name="Advance Auto Parts")),
        ("AMD", dict(name="Advanced Micro Devices")),
        ("AES", dict(name="AES")),
        ("AFL", dict(name="Aflac")),
        ("A", dict(name="Agilent Technologies")),
        ("APD", dict(name="Air Products and Chemicals")),
        ("AKAM", dict(name="Akamai Technologies")),
        ("ALK", dict(name="Alaska Air")),
        ("ALB", dict(name="Albemarle")),
        ("ARE", dict(name="Alexandria Real Estate Equities")),
        ("ALGN", dict(name="Align Technology")),
        ("ALLE", dict(name="Allegion")),
        ("LNT", dict(name="Alliant Energy")),
        ("ALL", dict(name="Allstate")),
        # ("GOOG", dict(name="Alphabet")),  # included above
        ("GOOGL", dict(name="Alphabet")),
        ("MO", dict(name="Altria")),
        # ("AMZN", dict(name="Amazon.com")),  # included above
        ("AMCR", dict(name="Amcor",
                      start_date=datetime(2019, 6, 11)  # before this, open == close == high == low, volume=0
                      )),
        ("AEE", dict(name="Ameren")),
        ("AAL", dict(name="American Airlines")),
        ("AEP", dict(name="American Electric Power")),
        ("AXP", dict(name="American Express")),
        ("AIG", dict(name="American International Group")),
        ("AMT", dict(name="American Tower")),
        ("AWK", dict(name="American Water Works")),
        ("AMP", dict(name="Ameriprise Financial")),
        ("ABC", dict(name="AmerisourceBergen")),
        ("AME", dict(name="AMETEK")),
        ("AMGN", dict(name="Amgen")),
        ("APH", dict(name="Amphenol")),
        ("ADI", dict(name="Analog Devices")),
        ("ANSS", dict(name="Ansys")),
        ("ANTM", dict(name="Anthem")),
        ("AON", dict(name="Aon")),
        ("APA", dict(name="APA Corporation")),
        # ("AAPL", dict(name="Apple")),  # included above
        ("AMAT", dict(name="Applied Materials")),
        ("APTV", dict(name="Aptiv")),
        ("ADM", dict(name="Archer-Daniels-Midland")),
        ("ANET", dict(name="Arista Networks")),
        ("AJG", dict(name="Arthur J Gallagher")),
        ("AIZ", dict(name="Assurant")),
        ("T", dict(name="AT&T")),

        # SSE 50 constituents, shown in Figure 4 of "They Still Haven't Told You" (2022)
        # Reference:  https://www.csindex.com.cn/en/indices/index-detail/000016#/indices/family/detail?indexCode=000016
        ("600000.SS", dict(name="Shanghai Pudong Development Bank")),
        ("600009.SS", dict(name="Shanghai International Airport")),
        ("600016.SS", dict(name="China Minsheng Banking Corp")),
        ("600028.SS", dict(name="China Petroleum & Chemical Corporation")),
        ("600030.SS", dict(name="CITIC Securities")),
        ("600031.SS", dict(name="Sany Heavy Industry")),
        ("600036.SS", dict(name="China Merchants Bank")),
        ("600048.SS", dict(name="Poly Developments and Holdings")),
        ("600050.SS", dict(name="China United Network Communications")),
        ("600104.SS", dict(name="SAIC Motor")),
        ("600196.SS", dict(name="Shanghai Fosun Pharmaceutical")),
        ("600276.SS", dict(name="Jiangsu Hengrui Medicine")),
        ("600309.SS", dict(name="Wanhua Chemical")),
        ("600436.SS", dict(name="Zhangzhou Pientzehuang Pharmaceutical")),
        ("600438.SS", dict(name="Tongwei")),
        ("600519.SS", dict(name="Kweichow Moutai")),
        ("600547.SS", dict(name="Shandong Gold Mining")),
        ("600570.SS", dict(name="Hundsun Technologies")),
        ("600585.SS", dict(name="Anhui Conch Cement")),
        ("600588.SS", dict(name="Yonyou Network Technology")),
        ("600690.SS", dict(name="Haier Smart Home")),
        ("600703.SS", dict(name="Sanan Optoelectronics")),
        ("600745.SS", dict(name="Wingtech Technology")),
        ("600809.SS", dict(name="Shanxi Xinghuacun Fen Wine Factory")),
        ("600837.SS", dict(name="Haitong Securities",  # Note:  sporadic prices from 1999-06-30 to 2002-05-14
                           )),
        ("600887.SS", dict(name="Inner Mongolia Yili Industrial Group")),
        ("600893.SS", dict(name="AECC Aviation Power",  # AVIC Aviation Engine
                           # Note:  no prices from 2006-12-04 to 2008-11-20
                           )),
        ("600900.SS", dict(name="China Yangtze Power")),
        ("600918.SS", dict(name="ZHONGTAI Securities")),
        ("601012.SS", dict(name="Longi Green Energy Technology")),
        ("601066.SS", dict(name="China Securities")),
        ("601088.SS", dict(name="China Shenhua Energy")),
        ("601138.SS", dict(name="Foxconn Industrial Internet")),
        ("601166.SS", dict(name="Industrial Bank")),
        ("601211.SS", dict(name="Guotai Junan Securities")),
        ("601288.SS", dict(name="Agricultural Bank of China")),
        ("601318.SS", dict(name="Ping An Insurance Company of China")),
        ("601336.SS", dict(name="New China Life Insurance")),
        ("601398.SS", dict(name="Industrial and Commercial Bank of China")),
        ("601601.SS", dict(name="China Pacific Insurance")),
        ("601628.SS", dict(name="China Life Insurance")),
        ("601633.SS", dict(name="Great Wall Motor")),
        ("601668.SS", dict(name="China State Construction Engineering")),
        ("601688.SS", dict(name="Huatai Securities")),
        ("601728.SS", dict(name="China Telecom")),
        ("601818.SS", dict(name="China Everbright Bank")),
        ("601857.SS", dict(name="PetroChina")),
        ("601888.SS", dict(name="China Tourism Group Duty Free")),
        ("601899.SS", dict(name="Zijin Mining Group")),
        ("601919.SS", dict(name="COSCO Shipping Holdings")),
        ("601995.SS", dict(name="China International Capital")),
        ("603259.SS", dict(name="WuXi AppTec",
                           start_date=datetime(2018, 5, 30)  # before this, open == close == high == low
                           )),
        ("603288.SS", dict(name="Foshan Haitian Flavouring and Food Company")),
        ("603501.SS", dict(name="Will Semiconductor Shanghai")),
        ("603986.SS", dict(name="GigaDevice Semiconductor Beijing",
                           start_date=datetime(2017, 3, 15)  # before this, open == close == high == low
                           )),

        # DAX constituents
        # Primary reference: https://companiesmarketcap.com/dax/largest-companies-by-market-cap/
        # Also: https://en.wikipedia.org/wiki/DAX, https://finance.yahoo.com/quote/%5EGDAXI/components/
        ("LIN.DE", dict(name="Linde")),
        ("SAP.DE", dict(name="SAP")),
        ("VOW3.DE", dict(name="Volkswagen")),
        ("SIE.DE", dict(name="Siemens")),
        ("ALV.DE", dict(name="Allianz")),
        ("DTE.DE", dict(name="Deutsche Telekom")),
        ("MRK.DE", dict(name="Merck")),
        ("AIR.DE", dict(name="Airbus")),
        ("MBG.DE", dict(name="Mercedes-Benz Group")),
        ("BAYN.DE", dict(name="Bayer")),
        ("SHL.DE", dict(name="Siemens Healthineers")),
        ("DPW.DE", dict(name="Deutsche Post")),
        ("BMW.DE", dict(name="BMW")),
        ("BAS.DE", dict(name="BASF")),
        ("ADS.DE", dict(name="Adidas")),
        ("IFX.DE", dict(name="Infineon Technologies")),
        ("MUV2.DE", dict(name="Munich Re")),
        ("VNA.DE", dict(name="Vonovia")),
        ("DB1.DE", dict(name="Deutsche Boerse")),  # Deutsche Börse
        ("RWE.DE", dict(name="RWE")),
        ("EOAN.DE", dict(name="E.ON")),
        ("HEN3.DE", dict(name="Henkel")),
        ("PAH3.DE", dict(name="Porsche")),
        ("SRT.DE", dict(name="Sartorius")),
        ("DBK.DE", dict(name="Deutsche Bank")),
        ("FRE.DE", dict(name="Fresenius")),
        ("BEI.DE", dict(name="Beiersdorf")),
        ("FME.DE", dict(name="Fresenius Medical Care")),
        ("SY1.DE", dict(name="Symrise")),
        ("ENR.DE", dict(name="Siemens Energy")),
        ("CON.DE", dict(name="Continental")),
        ("ZAL.DE", dict(name="Zalando")),
        ("BNR.DE", dict(name="Brenntag")),
        ("PUM.DE", dict(name="PUMA")),
        ("DHER.DE", dict(name="Delivery Hero")),
        ("QIA.DE", dict(name="Qiagen")),
        ("HEI.DE", dict(name="HeidelbergCement")),
        ("MTX.DE", dict(name="MTU Aero Engines")),
        ("1COV.DE", dict(name="Covestro")),
        ("HFG.DE", dict(name="HelloFresh")),
    ])


# Reference:  https://en.wikipedia.org/wiki/List_of_S&P_500_companies
US_COMPANIES_50_SYMS_DATE = datetime(2021, 12, 31)  # the date on which US_COMPANIES_50_SYMS is valid
US_COMPANIES_50_SYMS = ("MMM AOS ABT ABBV ABMD ACN ATVI ADBE AAP AMD AES AFL A APD AKAM ALK ALB ARE ALGN ALLE LNT ALL "
                        "GOOGL MO AMZN AEE AAL AEP AXP AIG AMT AWK AMP ABC AME AMGN APH ADI ANSS ANTM AON APA "
                        "AAPL AMAT APTV ADM ANET AJG AIZ T"
                        # Omitting GOOG (a near-duplicate of GOOGL) and AMCR (which has only a couple of years of data)
                        ).split()

# Reference:  https://www.csindex.com.cn/en/indices/index-detail/000016#/indices/family/detail?indexCode=000016
CHINA_SSE_50_SYMS_DATE = datetime(2021, 12, 31)  # the date on which CHINA_SSE_50_SYMS is valid
CHINA_SSE_50_SYMS = ("600000.SS 600028.SS 600030.SS 600031.SS 600036.SS "
                     "600048.SS 600050.SS 600104.SS 600196.SS 600276.SS "
                     "600309.SS 600436.SS 600438.SS 600519.SS 600547.SS "
                     "600570.SS 600585.SS 600588.SS 600690.SS 600745.SS "
                     "600809.SS 600837.SS 600887.SS 600893.SS 600900.SS "
                     "601012.SS 601066.SS 601088.SS 601138.SS 601166.SS "
                     "601211.SS 601288.SS 601318.SS 601336.SS 601398.SS "
                     "601601.SS 601628.SS 601633.SS 601668.SS 601688.SS "
                     # With only a few months of data for 601728.SS, we instead show 601818.SS 
                     # (which was in the SSE 50 before the Dec 2021 index update).
                     "601818.SS 601857.SS 601888.SS 601899.SS 601919.SS "  
                     "601995.SS 603259.SS 603288.SS 603501.SS 603986.SS").split()

# Reference:  https://companiesmarketcap.com/dax/largest-companies-by-market-cap/
DAX_SYMS = sorted(("LIN.DE SAP.DE VOW3.DE SIE.DE ALV.DE DTE.DE MRK.DE AIR.DE MBG.DE BAYN.DE SHL.DE DPW.DE BMW.DE "
                   "BAS.DE ADS.DE IFX.DE MUV2.DE VNA.DE DB1.DE RWE.DE EOAN.DE HEN3.DE PAH3.DE SRT.DE DBK.DE FRE.DE "
                   "BEI.DE FME.DE SY1.DE ENR.DE CON.DE ZAL.DE BNR.DE PUM.DE DHER.DE QIA.DE HEI.DE MTX.DE 1COV.DE "
                   "HFG.DE").split())

WORLD_INDICES_SYMS = ("SPY        ^IXIC       XIU.TO "
                      "STW.AX     EWZ         EWW "
                      "^IBEX      ^FCHI       ^GDAXI " 
                      "^AEX       OBXEDNB.OL  IMIB.MI "
                      "^TA125.TA  ^NSEI       ^BSESN "
                      "ES3.SI     ^KS11       ^TWII "
                      "^N225      ^HSI        000001.SS").split()

LINEAR_SCALES = {"percent", "fraction_of_unity", "currency"}
SHOW_LEGEND_1_EQ_100_PCT = False


##############################################################################################################
# Trivial helper routines
##############################################################################################################

def return_percent_to_string(r_pct):
    """
    Turn the return r_pct (expressed in units of percent) into a string suitable for display.

    @type r_pct: float
    @rtype: str
    """
    r_str = ("%+.2f%%" % r_pct if r_pct < -99 else  # show "-99.88%" (rather than "-100%")
             "%+.1f%%" % r_pct if -1 < r_pct < 1 else  # show "+0.2%" (because "+0%" looks like a mistake)
             "%+.0f%%" % r_pct if r_pct < 2e4 else  # show "+3333%"
             "+" + "{:,.0f}".format(r_pct) + "%")   # show "+333,333%"
    return (" " if r_pct < 0 else "") + r_str


def return_fraction_of_unity_to_string(r):
    """
    Turn the return r (expressed as a fraction of unity) into a string suitable for display.

    @type r: float
    @rtype: str
    """
    r_str = ("%+.4f" % r if r < -0.99 else  # show "-0.9988" (rather than "-1.00")
             "%+.3f" % r if -0.01 < r < 0.01 else  # show "+0.002" (because "+0.00" looks like a mistake)
             "%+.2f" % r if r < 2e2 else  # show "+33.33"
             "+" + "{:,.0f}".format(r))  # show "+3,333"
    return (" " if r < 0 else "") + r_str


def format_money_as_string(m, currency_sym=None):
    """
    Turn the float m into a string suitable for display.

    @type m: float
    @type currency_sym: str
    @rtype: str
    """
    money_as_string = ("%.4f" % m if m < 1.95e-3 else  # show "0.0013" (rather than "0.00")
                       "%.3f" % m if m < 1e-2 else  # show "0.003" (rather than "0.00")
                       "%.2f" % m if m < 1e2 else  # show "3.12"
                       "%.0f" % m if m < 1e4 else  # show "123" (rather than "123.45")
                       '{:,}'.format(int(m))  # show "12,345" (rather than "12345.67")
                       )
    return (currency_sym or "") + money_as_string


def linear_scale_start_value(linear_scale):
    """
    Return the value at which the overnight/intraday curves start.

    @type linear_scale: str
    @rtype: float
    """
    assert linear_scale in LINEAR_SCALES, linear_scale
    return dict(percent=0, fraction_of_unity=0, currency=1)[linear_scale]


def get_data_filename(sym):
    """
    Get the name of the local file with open and close prices for sym.

    @type sym: str
    @rtype: str
    """
    return os.path.join(INPUT_DATA_DIR, sym + ".csv")


def get_date_range_str(start_date=None, end_date=None):
    """
    @type start_date: datetime or None
    @type end_date: datetime or None
    @rtype: str
    """
    return "%s-%s" % ((start_date or DEFAULT_START_DATE).strftime("%Y%m%d"),
                      (end_date or DEFAULT_END_DATE).strftime("%Y%m%d"))


def cumulate_returns(returns):
    """
    Cumulate returns.

    @type returns: list[float]
    @rtype: list[float]
    """
    r0 = 0
    cumulated = []
    for r1 in returns:
        r0 = (1 + r0) * (1 + r1) - 1
        cumulated.append(r0)
    return cumulated


def sym_to_currency_tex(sym):
    """
    Return the (latex) currency symbol for the country in which sym trades.

    @type sym: str
    @rtype: str
    """
    exchange = "US" if len(sym.split(".")) == 1 else sym.split(".")[1]
    return dict(US="$", HK="HK$", SS="CN$\yen$").get(exchange)


def word_wrapped_company_name(sym):
    """
    Return sym's company name, word wrapped to fit in Figure 3 or 4 of "They Still Haven't Told You" (2022).

    The logic of this function is whatever it needs to be to make sure the company names in Figures 3 and 4 are legible.

    @type sym: str
    @rtype: str
    """
    s_name = symbol_details_dict().get(sym).get("name")
    s_name_words = s_name.split()
    if len(s_name_words) >= 5:
        s_name = " ".join(s_name_words[:3]) + "\n" + " ".join(s_name_words[3:])
    elif len(s_name_words) == 4 and len(s_name) >= 26:
        l2x2 = max(len(" ".join(s_name_words[:2])), len(" ".join(s_name_words[2:])))
        l3x1 = max(len(" ".join(s_name_words[:3])), len(" ".join(s_name_words[3:])))
        i_word_break = 2 if l2x2 < l3x1 else 3
        s_name = " ".join(s_name_words[:i_word_break]) + "\n" + " ".join(s_name_words[i_word_break:])
    elif len(s_name_words) == 3 and len(s_name) >= 26:
        s_name = " ".join(s_name_words[:2]) + "\n" + " ".join(s_name_words[2:])
    return s_name


def clip(x, lo, hi):
    """Clip x to the range (lo, hi)."""
    return (lo if x < lo else
            hi if x > hi else
            x)


def force_full_horizontal_axis(ax, start_date=None, end_date=None):
    """
    Make sure the horizontal axis goes from start_date (or DEFAULT_START_DATE) to end_date (or DEFAULT_END_DATE).

    @type ax: matplotlib.axes.Axes
    @type start_date: datetime
    @type end_date: datetime
    """
    # Draw an invisible horizontal line across the full date range we want the plot to span.
    ax.plot_date([date2num(start_date or DEFAULT_START_DATE), date2num(end_date or DEFAULT_END_DATE)],
                 ([1, 1] if ax.get_yscale() == "log" else [0, 0]),
                 fmt='w', alpha=0)


def no_box(ax, keep_yticks=False):
    """
    Remove the frame around the subplot ax.

    @type ax: matplotlib.axes.Axes
    @type keep_yticks: bool
    """
    for side in "top left right".split():
        ax.spines[side].set_visible(False)
    if not keep_yticks:
        ax.set_yticks([])
        ax.set_yticklabels([])


##############################################################################################################
# Process data
##############################################################################################################

def download_data_from_yahoo_finance(sym):
    """
    Download historical open/close data for sym from Yahoo! Finance.

    Example: https://query1.finance.yahoo.com/v7/finance/download/SPY? ...
                ... period1=631170000&period2=1599022800&interval=1d&events=history&includeAdjustedClose=true

    Note:  Yahoo! Finance occasionally changes something that breaks this download.
           If you find this routine broken, please email me with the error, and I will try to find a fix.

    @type sym: str
    @rtype: None
    """
    d1 = DEFAULT_START_DATE
    d2 = (symbol_details_dict().get(sym).get("end_date") or DEFAULT_END_DATE) + timedelta(days=1)
    url_params = dict(interval="1d", events="history",
                      period1=int(mktime((d1.year, d1.month, d1.day, 0, 0, 0, 0, 0, 0))),
                      period2=int(mktime((d2.year, d2.month, d2.day, 0, 0, 0, 0, 0, 0))),
                      includeAdjustedClose="true")
    my_url = ("https://query1.finance.yahoo.com/v7/finance/download/%s?" % urllib.quote(sym)
              ) + urllib.urlencode(url_params)
    r_headers = {"User-Agent": 'Mozilla/5.0 (Windows; U; Windows NT 5.0; en-GB; rv:1.8.1.12) '
                               'Gecko/20080201 Firefox/2.0.0.12'}
    print("Downloading %s data from Yahoo! Finance." % sym)
    r = requests.get(my_url, headers=r_headers)
    if "404 not found" in r.content:
        print("Yahoo Finance did not provide the data we expect.  Waiting for a bit before retrying.")
        sleep(30)
        print("Downloading %s data from Yahoo! Finance." % sym)
        r = requests.get(my_url, headers=r_headers)

    file(get_data_filename(sym), "w").write(r.content)
    assert r.content.split("\n")[0] == "Date,Open,High,Low,Close,Adj Close,Volume", (
            "Yahoo Finance did not provide the data we expect.  The contents of %s should contain a clue "
            "as to what the problem is." % get_data_filename(sym))
    # If we will be downloading multiple files from Yahoo! Finance, do not be obnoxious about it.
    sleep(7)


def download_data_from_archive(sym, archive_date):
    """
    Download historical Yahoo! Finance open/close data for sym from our archive.

    @type sym: str
    @param archive_date: yyyymmdd  (e.g., "20201231")
    @type archive_date: str
    @rtype: None
    """
    print("Downloading %s data from %s archive." % (sym, archive_date))
    my_url = "https://bruceknuteson.github.io/spy-day-and-night/open_close_price_data/%s/%s.csv" % (archive_date, sym)
    r = requests.get(my_url)
    file(get_data_filename(sym), "w").write(r.content)


def get_historical_open_close_data(sym):
    """
    Return Yahoo! Finance's historical open/close price data for sym.

    Download the data if necessary.

    @type sym: str
    @rtype: list[str]
    """
    data_filename = get_data_filename(sym)
    # To use the ASX 200 (STW.AX) and Straits Times (ES3.SI) data that were available on Yahoo Finance on 2020-12-31,
    # set patch_longer_history = {"STW.AX", "ES3.SI"}
    patch_longer_history = set()  # {"STW.AX", "ES3.SI"}
    if not os.path.exists(data_filename):
        download_data_from_yahoo_finance(sym)
        if sym == "ISFU.L":
            # As of 2019-10-31, Yahoo! Finance provided sensible data for ISFU.L from 2001-01-02 to 2018-06-20.
            # Yahoo! Finance no longer provides sensible historical data for any of ISFU.L, ISF.L, or ^FTSE.  To get
            # reasonable FTSE 100 data, we download Yahoo! Finance's data for ISFU.L as of 2019-10-31 from our archive.
            download_data_from_archive(sym, "20191031")
        if sym in patch_longer_history:
            # Yahoo! Finance provided a longer history for STW.AX and ES3.SI on 2020-12-31 than it does now.
            # If desired, download a longer history for STW.AX and/or ES3.SI from our archive.
            download_data_from_archive(sym, "20201231")
    data = open(data_filename).read().split("\n")
    # double-check the header
    assert data[0].strip() == "Date,Open,High,Low,Close,Adj Close,Volume", data[0]
    return data


def get_prices_open_close_adj_dates(original_data, start_date=None, end_date=None, bad_data_dates=None):
    """
    Get (price_open, price_close, price_close_adj, dates_datetime) from the open and close prices in original_data.

    @type original_data: list[str]

    @param start_date: provided if data before start_date are suspect
    @type start_date: datetime

    @param end_date: provided if data after end_date are suspect (or unavailable)
    @type end_date: datetime or None

    @param bad_data_dates: provided if data for specific dates are suspect
    @type bad_data_dates: list[datetime]

    @return: (price_open, price_close, price_close_adj, dates_datetime)
    @rtype: (list[float], list[float], list[float], list[datetime])
    """
    # Make sure the header is what we expect.
    assert original_data[0].strip() == "Date,Open,High,Low,Close,Adj Close,Volume", original_data[0]

    # Remove any known bad dates.
    bad_data_dates_str = set(d.strftime(DATETIME_FORMAT) for d in (bad_data_dates or []))
    data = [d.split(',') for d in original_data[1:]
            if d and "null" not in d and d.split(',')[0] not in bad_data_dates_str]

    # Also discard any dates with open = high = low = close.
    data = [d for d in data if len(set(d[1:5])) > 1]
    # Also discard any dates with open = 0.
    data = [d for d in data if float(d[1]) > 0]

    price_open = [float(d[1]) for d in data]  # Open
    price_close = [float(d[4]) for d in data]  # Close
    price_close_adj = [float(d[5]) for d in data]  # Adj Close
    assert all(p > 0 for p in price_close_adj), "Bad data: negative adjusted close price"
    dates_datetime = [datetime(*map(int, d[0].split('-'))) for d in data]  # Date

    # In some cases (like the DAX before 1993-12-14), price_open == price_close because Yahoo! Finance does not have
    # opening prices.  If we are dealing with data like the DAX starting on 1993-01-01, recognize this, and
    # only return data from 1993-12-14 onward.
    # Separately, only consider dates from start_date onward.
    d0 = max([p_open != p_close for (p_open, p_close) in zip(price_open, price_close)].index(True),
             [d >= (start_date or DEFAULT_START_DATE) for d in dates_datetime].index(True))
    # Only consider dates up to end_date.
    d1 = ([d > (end_date or DEFAULT_END_DATE) for d in dates_datetime].index(True)
          if (end_date or DEFAULT_END_DATE) < max(dates_datetime) else len(dates_datetime))
    if d0 > 1 or d1 < len(dates_datetime):
        price_open = price_open[d0:d1]
        price_close = price_close[d0:d1]
        price_close_adj = price_close_adj[d0:d1]
        dates_datetime = dates_datetime[d0:d1]

    return price_open, price_close, price_close_adj, dates_datetime


def compute_returns_overnight_intraday(price_open, price_close, price_close_adj, dates_datetime):
    """
    Compute overnight and intraday returns from open and close prices.

    @type price_open: list[float]
    @type price_close: list[float]
    @type price_close_adj: list[float]
    @type dates_datetime: list[datetime]

    @return: (returns_overnight, returns_intraday)
    @rtype: (list[float], list[float])
    """
    assert len(price_open) == len(price_close) == len(price_close_adj) == len(dates_datetime)
    n_days = len(dates_datetime)
    if n_days == 0:
        return [], []

    # Intraday returns are the returns from open to close.
    # returns_intraday[0] is the return from open on dates_datetime[0] to close on dates_datetime[0]
    returns_intraday = [price_close[i] / price_open[i] - 1 for i in range(n_days)]

    # Use adjusted prices to get close to close returns.
    # returns_close_to_close[1] is the return from close on dates_datetime[0] to close on dates_datetime[1]
    returns_close_to_close = [0.] + [price_close_adj[i] / price_close_adj[i-1] - 1 for i in range(1, n_days)]

    # Overnight returns are close to close returns sans intraday returns.
    # returns_overnight[1] is the return from close on dates_datetime[0] to open on dates_datetime[1]
    returns_overnight = [0.] + [(1 + returns_close_to_close[i]) / (1 + returns_intraday[i]) - 1
                                # A big time gap (let's say two weeks or more) means we are missing data.
                                # We should not attribute the total return over this time gap to overnight.
                                if dates_datetime[i] - dates_datetime[i-1] < timedelta(days=14) else 0
                                for i in range(1, n_days)]

    return returns_overnight, returns_intraday


class PlotData(object):
    """The data necessary to make a plot of cumulative overnight and intraday returns."""
    def __init__(self, dates_datetime, returns_overnight, returns_intraday):
        """
        returns_intraday[i] is the return from market open to market close on dates_datetime[i].
        returns_overnight[i] is the return from market close on dates_datetime[i-1] to market open on dates_datetime[i].

        @type dates_datetime: list[datetime]
        @type returns_overnight: list[float]
        @type returns_intraday: list[float]
        """
        assert len(dates_datetime) == len(returns_overnight) == len(returns_intraday), (
            len(dates_datetime), len(returns_overnight), len(returns_intraday))
        assert returns_overnight[0] == 0
        self._dates_datetime = list(dates_datetime)
        self._returns_overnight = list(returns_overnight)
        self._returns_intraday = list(returns_intraday)

    @property
    def n_days(self):
        """@rtype: int"""
        return len(self._dates_datetime)

    @property
    def first_date(self):
        """@rtype: datetime"""
        return self._dates_datetime[0]

    @property
    def last_date(self):
        """@rtype: datetime"""
        return self._dates_datetime[-1]

    def plot_data(self, ax, vertical_scale="linear", linear_scale="percent"):
        """
        Plot the cumulative overnight and intraday returns on the axis ax,
        with either linear or logarithmic vertical scale.

        @type ax: matplotlib.axes.Axes
        @type vertical_scale: str
        @type linear_scale: str
        @return: (overnight_curve, intraday_curve)
        @rtype: (list[float], list[float])
        """
        assert vertical_scale in "linear log".split(), vertical_scale
        if vertical_scale == "linear":
            assert linear_scale in LINEAR_SCALES, linear_scale
        vertical_choice = dict(linear=linear_scale, log="log")[vertical_scale]
        r_func = dict(percent=(lambda r1: r1 * 100),  # show return in units of percent
                      currency=(lambda r1: r1 + 1),  # show return as "this is what $1 turns into"
                      fraction_of_unity=(lambda r1: r1),  # show return as a fraction of unity
                      log=(lambda r1: r1 + 1)  # show return as "this is what $1 turns into", log scale
                      )[vertical_choice]
        overnight_curve = [r_func(r) for r in cumulate_returns(self._returns_overnight)]
        intraday_curve = [r_func(r) for r in cumulate_returns(self._returns_intraday)]
        dates_datenum = map(date2num, self._dates_datetime)
        assert overnight_curve[0] == r_func(0)  # just making sure we have what we expect
        ax.margins(x=0, y=0)
        ax.plot_date(dates_datenum, overnight_curve, fmt='-b', linewidth=1.5)
        ax.plot_date(dates_datenum, intraday_curve, fmt='-g', linewidth=1.5)
        if vertical_scale == "log":
            ax.set_yscale('log')
        return overnight_curve, intraday_curve

    def histogram_returns(self):
        """Histogram the distribution of overnight and intraday returns."""
        assert len(self._returns_overnight) == len(self._returns_intraday)
        assert self._returns_overnight[0] == 0  # no need to include this
        r = 3  # the horizontal axis of the histogram extends from -3% to +3%
        c = r - 0.07  # put underflow and overflow in the leftmost and rightmost bins, respectively
        n_bins = 10 * r * 2  # the histogram bin width is 0.1%
        hist([clip(r1 * 1e2, -c, +c) for r1 in self._returns_overnight[1:]],
             bins=n_bins, range=(-r, +r), color="b", histtype="step", label="overnight")
        hist([clip(r1 * 1e2, -c, +c) for r1 in self._returns_intraday],
             bins=n_bins, range=(-r, +r), color="g", histtype="step", label="intraday")
        xlim(-(r + 0.03), r + 0.03)


def get_plot_data(sym, start_date=None):
    """
    Extract the returns we want to plot from historical open and close prices.

    @type sym: str
    @type start_date: datetime
    @rtype: PlotData
    """
    data = get_historical_open_close_data(sym)
    s = symbol_details_dict().get(sym)
    (price_open, price_close, price_close_adj, dates_datetime) = get_prices_open_close_adj_dates(
        data, (start_date or s.get("start_date")), s.get("end_date"), s.get("bad_data_dates"))
    returns_overnight, returns_intraday = compute_returns_overnight_intraday(
        price_open, price_close, price_close_adj, dates_datetime)
    return PlotData(dates_datetime, returns_overnight, returns_intraday) if dates_datetime else None


def get_plot_date_range_for_inclusion_in_caption(first_date_of_data, sym_details):
    """
    If the date range of data for this plot is non-trivially different from DEFAULT_START_DATE onward,
    return a string that we can insert into the relevant figure caption (or a footnote).

    @type first_date_of_data: datetime
    @type sym_details: dict
    @rtype: str
    """
    if first_date_of_data and (first_date_of_data - DEFAULT_START_DATE) > timedelta(days=10):
        date_str = first_date_of_data.strftime(DATETIME_FORMAT)
        if sym_details.get("end_date"):
            date_str += " to " + sym_details.get("end_date").strftime(DATETIME_FORMAT)
        plot_label_str = sym_details.get("country")
        if plot_label_str in ["United States", "India"]:  # insufficiently specific
            plot_label_str = sym_details.get("short_name") or sym_details.get("name")
        return "%s (%s)" % ((sym_details.get("name") or plot_label_str).replace("&", r"\&"), date_str)


##############################################################################################################
# Make plots:  linear scale
##############################################################################################################

def plot_overnight_intraday_returns_linear_scale(plot_data, ax, linear_scale="percent"):
    """
    Draw a plot of cumulative overnight and intraday returns.

    @type plot_data: PlotData
    @type ax: matplotlib.axes.Axes
    @param linear_scale:  If "percent", show cumulative returns in units of percent (e.g., "+123%").
                          If "fraction_of_unity", show cumulative returns as a fraction of unity (e.g., "+1.23").
                          If "currency", show cumulative returns in terms of what one unit of local currency would
                                         turn into (e.g., "+2.23").
    @type linear_scale: str
    """
    assert linear_scale in LINEAR_SCALES, linear_scale
    overnight_curve, intraday_curve = plot_data.plot_data(ax, linear_scale=linear_scale)
    # Add yticks on the right edge of the plot.
    todays_value_overnight_y = todays_value_overnight = overnight_curve[-1]
    todays_value_intraday_y = todays_value_intraday = intraday_curve[-1]
    # If the cumulative overnight and intraday values are very close together, the text will overlap on the plot,
    # making the values hard to read.  In this case, we want to shift the position of the text slightly, to make sure
    # the final cumulative values are easy to read.  (Here, todays_value_{overnight,intraday} is the final value, and
    # todays_value_{overnight,intraday}_y is the position of the text that we may want to shift.)
    max_y = max(max(overnight_curve), max(intraday_curve))
    y_bottom = dict(percent=-100, fraction_of_unity=-1, currency=0)[linear_scale]
    min_y_sep = 0.1 * (max_y - y_bottom)
    d = todays_value_overnight - todays_value_intraday
    if abs(d) < min_y_sep:
        todays_value_overnight_y += ((min_y_sep - abs(d)) / 2.) * (+1 if d >= 0 else -1)
        todays_value_intraday_y += ((min_y_sep - abs(d)) / 2.) * (-1 if d >= 0 else +1)
    ytick_right_x = xlim()[0] + (xlim()[-1] - xlim()[0]) * 1.005
    r_format_func = dict(percent=return_percent_to_string,
                         fraction_of_unity=return_fraction_of_unity_to_string,
                         currency=format_money_as_string)[linear_scale]
    ax.text(ytick_right_x, todays_value_overnight_y, r_format_func(todays_value_overnight), verticalalignment="center")
    ax.text(ytick_right_x, todays_value_intraday_y, r_format_func(todays_value_intraday), verticalalignment="center")
    # Set yticks on the left side of the plot.
    ytick_left = linear_scale_start_value(linear_scale)
    ax.set_yticks([ytick_left])
    ax.set_yticklabels([ytick_left])
    ax.set_ylim(y_bottom)


def plot_overnight_intraday_returns_world_indices_linear_scale(linear_scale="fraction_of_unity"):
    """
    Make Figure 2 of "They Still Haven't Told You" (2022)
    [also Figure 1 of "Strikingly Suspicious Overnight and Intraday Returns" (2020)],
    showing overnight and intraday returns to the world's major stock market indices.

    @type linear_scale: str
    """
    assert linear_scale in LINEAR_SCALES, linear_scale
    clf()
    n_rows, n_cols = 7, 3
    fig, axes = subplots(num=1, nrows=n_rows, ncols=n_cols, sharex=True)
    for i_s, sym in enumerate(WORLD_INDICES_SYMS):
        ax = axes[(i_s // n_cols), (i_s % n_cols)]
        plot_data = get_plot_data(sym)
        plot_overnight_intraday_returns_linear_scale(plot_data, ax, linear_scale=linear_scale)
        no_box(ax)
        ax.xaxis.set_major_locator(YearLocator(5))
        # label the plot
        s = symbol_details_dict().get(sym)
        ax.text(0.05, 0.80, s.get("country") + "\n" + s.get("name"),
                transform=ax.transAxes, horizontalalignment="left", verticalalignment="top", fontsize="large")
        if i_s == 0:  # show value where the blue and green curves start at the left of the top left plot
            v = linear_scale_start_value(linear_scale)
            ax.text(plot_data.first_date - timedelta(days=500), v, str(v), verticalalignment="center")
        ax.set_zorder(1000 - 10 * i_s)

    # Make sure the horizontal axis goes from DEFAULT_START_DATE to DEFAULT_END_DATE.
    force_full_horizontal_axis(axes[-1, -1])
    # Add figure title and legend.
    ax = axes[0, 0]
    ax.legend(("overnight", "intraday"), loc='lower left', bbox_to_anchor=(0.00, 1.00), frameon=False)
    if SHOW_LEGEND_1_EQ_100_PCT and linear_scale == "fraction_of_unity":
        ax.text(0.08, 1.025, "1 = 100%", transform=ax.transAxes, verticalalignment="top", fontsize="small")
    if linear_scale == "currency":
        fig.text(0.52, 0.90, ("Value of one unit of local currency invested in major stock market indices,\n"
                              "getting only overnight or intraday returns"), fontsize="x-large",
                 horizontalalignment="center", verticalalignment="center", transform=fig.transFigure)
    else:
        fig.text(0.52, 0.90, "Overnight and Intraday Returns to Major Stock Market Indices", fontsize="xx-large",
                 horizontalalignment="center", verticalalignment="center", transform=fig.transFigure)
    fig.set_size_inches(15.32, 19, forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "jpg png pdf".split():
            fn = "world_indices_%s.%s" % (get_date_range_str(), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=300)
        # also save a lower resolution png file (which is better for some web pages)
        savefig(os.path.join(OUTPUT_PLOT_DIR, "world_indices_144dpi.png"), bbox_inches="tight", dpi=144)


def plot_overnight_intraday_returns_sym_standalone(sym, plot_format="pdf"):
    """
    Draw a plot of cumulative returns for the symbol sym.

    @type sym: str
    @type plot_format: str
    """
    sym_details = symbol_details_dict().get(sym)
    # Get the data.
    plot_data = get_plot_data(sym)

    # Make the plot.
    fig = figure(1)
    ax = gca()
    plot_overnight_intraday_returns_linear_scale(plot_data, ax)
    min_plot_date = datetime(sym_details.get("start_date", plot_data.first_date).year, 1, 1)
    ax.xaxis.set_major_locator(YearLocator(5 if min_plot_date < datetime(1995, 1, 1) else
                                           2 if min_plot_date <= datetime(2010, 1, 1) else
                                           1))

    # Add finishing touches.
    ax.legend(("overnight", "intraday"), loc='upper left', bbox_to_anchor=(0.00, 1.00), fontsize="large")
    fig.text(0.52, 0.90, (sym_details.get("name") + " Overnight and Intraday Returns"),
             horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize="x-large")
    fig.set_size_inches(8.0, 4.2, forward=True)
    if OUTPUT_PLOT_DIR:
        s = (sym_details.get("short_name") or sym_details.get("name")).lower()
        if len(s) > 20:
            s = sym.lower()
        s = re.sub("[ &^]", "", s)
        fn = "linear_%s.%s" % (s, plot_format)
        savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight")


def plot_overnight_intraday_returns_world_indices_standalone():
    """Make a standalone overnight/intraday plot for each of the world's major stock market indices."""
    for sym in WORLD_INDICES_SYMS:
        clf()
        plot_overnight_intraday_returns_sym_standalone(sym)


def plot_overnight_intraday_returns_us_companies_largest(start_date=datetime(2010, 1, 1)):
    """
    Make Figure 2 of "They Chose to Not Tell You" (2021),
    showing overnight/intraday plots for several of the largest companies in the United States.

    Primary reference:  https://en.wikipedia.org/wiki/List_of_public_corporations_by_market_capitalization
    See also:
      + https://companiesmarketcap.com/usa/largest-companies-in-the-usa-by-market-cap/
      + https://www.iweblists.com/us/commerce/MarketCapitalization.html

    @type start_date: datetime
    """
    clf()
    n_rows, n_cols = 3, 3
    n_total = n_rows * n_cols
    fig, axes = subplots(num=2, nrows=n_rows, ncols=n_cols, sharex=True)
    largest_us_companies = "AAPL MSFT GOOG AMZN TSLA FB NVDA BRK-B UNH V JPM".split()[:n_total]
    largest_us_companies_as_of_date = datetime(2021, 12, 31)  # the date we last updated largest_us_companies
    for i_s, sym in enumerate(largest_us_companies):
        sym = largest_us_companies[i_s]
        ax = axes[(i_s // n_cols), (i_s % n_cols)]
        plot_data = get_plot_data(sym, start_date)
        plot_overnight_intraday_returns_linear_scale(plot_data, ax)
        ax.xaxis.set_major_locator(YearLocator(5))
        no_box(ax)
        # label the plot
        ax.text(0.07, 0.85, (symbol_details_dict().get(sym).get("name") + " (%s)" % sym),
                transform=ax.transAxes, horizontalalignment="left", verticalalignment="top", fontsize="large")
        # Put each plot in front of the plot to its right,
        # so we don't cut off the cumulative returns on the right edge of the plot
        ax.set_zorder(1000 - 10 * i_s)

    # Add figure title and legend.
    axes[0, 0].legend(("overnight", "intraday"), loc='upper left', bbox_to_anchor=(0.06, 1.25))
    fig.text(0.52, 0.91, "Overnight and Intraday Returns to the Largest S&P 500 Stocks",
             horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize="x-large")
    fig.text(0.52, 0.907, 'by market cap on %s' % largest_us_companies_as_of_date.strftime("%B %d, %Y"),
             horizontalalignment="center", verticalalignment="top", transform=fig.transFigure, fontsize="x-small")
    fig.set_size_inches((0.16 + 5 * n_cols), (3 * n_rows), forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "pdf png".split():
            fn = "us_companies_largest_%s.%s" % (get_date_range_str(start_date), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


def plot_overnight_intraday_returns_what_you_would_expect(linear_scale="fraction_of_unity"):
    """
    Make Figure 1 of "They Still Haven't Told You" (2022), showing what you would expect overnight/intraday returns
    to look like if prices moved like a random walk and returns were due to the bearing of risk.

    @type linear_scale: str
    """
    assert linear_scale in LINEAR_SCALES, linear_scale

    # Feel free/encouraged to modify these parameters to see how things change.
    start_date = DEFAULT_START_DATE
    random_seed = 0  # random number seed
    expected_return_per_year = 0.07  # mu = 7%/year
    expected_volatility_per_sqrt_year = 0.20  # sigma = 20%/sqrt(year)
    cumulative_return_needed_to_survive = 3.  # only keep plots with total return >= +300%
    # The fraction of a day's price variance that realizes overnight can also be changed, but only in a limited range
    # (to remain consistent with the value realized in the world's stock markets).
    fraction_of_price_variance_realized_overnight = 1. / 3

    # Given the parameters above, calculate some useful quantities and assert that things make sense.
    days_per_year = 365.25 * 5/7  # In this toy world, the market is open Monday through Friday every week of the year.
    expected_return_per_day = expected_return_per_year / days_per_year
    fraction_of_price_variance_realized_intraday = 1 - fraction_of_price_variance_realized_overnight
    # In all indices and individual stocks over the time period we consider,
    # the distribution of intraday returns is wider than the distribution of overnight returns.
    assert fraction_of_price_variance_realized_overnight < fraction_of_price_variance_realized_intraday, (
        "In the world's stock markets, prices move more intraday (between market open and market close) "
        "than they do overnight (between market close and market open).  "
        "See for example Figure 4 of 'They Chose to Not Tell You' (2021).")
    o_i = fraction_of_price_variance_realized_overnight / fraction_of_price_variance_realized_intraday
    assert 0.25 <= o_i < 0.75, "fraction_of_price_variance_realized_overnight is not reasonable"
    # Returns are due to the bearing of risk.
    expected_return_per_overnight_period = expected_return_per_day * fraction_of_price_variance_realized_overnight
    expected_return_per_intraday_period = expected_return_per_day * fraction_of_price_variance_realized_intraday
    expected_volatility_per_sqrt_day = expected_volatility_per_sqrt_year / sqrt(days_per_year)
    expected_volatility_one_overnight_period = (expected_volatility_per_sqrt_day *
                                                sqrt(fraction_of_price_variance_realized_overnight))
    expected_volatility_one_intraday_period = (expected_volatility_per_sqrt_day *
                                               sqrt(fraction_of_price_variance_realized_intraday))
    assert (sqrt(expected_volatility_one_overnight_period ** 2 + expected_volatility_one_intraday_period ** 2) *
            sqrt(days_per_year) == expected_volatility_per_sqrt_year)
    # As a final check, make sure this isn't going to take too long.
    n_days_total = (DEFAULT_END_DATE - start_date).days * 5./7  # only weekdays
    x = ((expected_return_per_day * n_days_total - cumulative_return_needed_to_survive) /
         (expected_volatility_per_sqrt_day * sqrt(n_days_total)))
    # (see e.g. https://stats.stackexchange.com/a/187909)
    fraction_of_plots_we_generate_that_we_expect_to_survive = (1 + erf(x/sqrt(2))) / 2
    assert (fraction_of_plots_we_generate_that_we_expect_to_survive > 1e-3), (
        "this is going to take too long", fraction_of_plots_we_generate_that_we_expect_to_survive)

    clf()
    n_rows, n_cols = 10, 5
    n_total = n_rows * n_cols
    fig, axes = subplots(num=2, nrows=n_rows, ncols=n_cols, sharex=True)

    random.seed(random_seed)  # to make a reproducible plot, explicitly seed the random number generator.
    for i in range(n_total):
        ax = axes[(i // n_cols), (i % n_cols)]
        while True:
            d = start_date
            returns_overnight = []
            returns_intraday = []
            dates_datetime = []
            total_return = 0.
            while d <= DEFAULT_END_DATE:
                if d.weekday() < 5:  # Monday through Friday
                    dates_datetime.append(d)
                    returns_overnight.append(random.gauss(expected_return_per_overnight_period,
                                                          expected_volatility_one_overnight_period)
                                             # there is no overnight return on the very first day
                                             if returns_overnight else 0.)
                    returns_intraday.append(random.gauss(expected_return_per_intraday_period,
                                                         expected_volatility_one_intraday_period))
                    total_return = (1 + total_return) * (1 + returns_overnight[-1]) * (1 + returns_intraday[-1]) - 1
                d += timedelta(days=1)
            if total_return > cumulative_return_needed_to_survive:
                break  # this one is a survivor
        plot_data = PlotData(dates_datetime, returns_overnight, returns_intraday)
        plot_overnight_intraday_returns_linear_scale(plot_data, ax, linear_scale=linear_scale)
        ax.xaxis.set_major_locator(YearLocator(10))
        no_box(ax)
        if i == 0:  # show the value where the blue and green curves start at the left of the top left plot
            v = linear_scale_start_value(linear_scale)
            ax.text(plot_data.first_date - timedelta(days=120), v, str(v),
                    verticalalignment="center", horizontalalignment="right")
        ax.set_zorder(1000 - 10 * i)

    # Add figure title and legend.
    ax = axes[0, 0]
    ax.legend(("overnight", "intraday"), loc='upper left', bbox_to_anchor=(0.02, 1.30), fontsize="large", frameon=False)
    if SHOW_LEGEND_1_EQ_100_PCT and linear_scale == "fraction_of_unity":
        ax.text(0.14, 0.845, "1 = 100%", transform=ax.transAxes, verticalalignment="top")
    if linear_scale == "currency":
        fig.text(0.52, 0.91, ("Value of one unit of currency invested in an efficient market, "
                              "getting only overnight or intraday returns"),
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=20)
    else:
        fig.text(0.52, 0.91, "This is what overnight and intraday returns should look like",
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=24)
    fig.text(0.52, 0.9075,
             ('in a toy world with $\mu=%(mu_pct)s\ /\ {\\rm year}$, '
              '$\sigma= %(sigma_pct)s\ /\ \sqrt{\\rm year}$, '
              'overnight variance / intraday variance = %(overnight_intraday)s, and '
              'discarding all plots with total return $<%(survivor)s$ ($%(survivor_pct)s$) '
              'to crudely model survivorship bias' %
              dict(mu_pct="%.0f" % (expected_return_per_year*1e2) + "\%",
                   sigma_pct="%.0f" % (expected_volatility_per_sqrt_year*1e2) + "\%",
                   overnight_intraday=("1 / 2" if 0.49 < o_i < 0.51 else "%0.2f" % o_i),
                   survivor="%+.2f" % cumulative_return_needed_to_survive,
                   survivor_pct="%+.0f" % (cumulative_return_needed_to_survive*1e2) + "\%")),
             horizontalalignment="center", verticalalignment="top", transform=fig.transFigure, fontsize="small")
    fig.set_size_inches((0.12 + 4 * n_cols), (2.4 * n_rows), forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "pdf png".split():
            fn = "what_you_would_expect.%s" % plot_format
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


def plot_overnight_intraday_returns_us_companies_50(linear_scale="fraction_of_unity"):
    """
    Make Figure 3 of "They Still Haven't Told You" (2022), showing overnight/intraday plots
    for the first 50 companies (sorted alphabetically by company name) in the US S&P 500 index.

    Reference:  https://en.wikipedia.org/wiki/List_of_S&P_500_companies

    @type linear_scale: str
    """
    assert linear_scale in LINEAR_SCALES, linear_scale
    start_date = DEFAULT_START_DATE
    clf()
    n_rows, n_cols = 10, 5
    n_total = n_rows * n_cols
    fig, axes = subplots(num=2, nrows=n_rows, ncols=n_cols, sharex=True)
    fig.subplots_adjust(wspace=0.25)  # increase the spacing between plots to accommodate some large cumulative returns
    for i_s in range(n_total)[::-1]:  # make the grid of plots in reverse order so cumulative returns are not cut off
        sym = US_COMPANIES_50_SYMS[i_s]
        ax = axes[(i_s // n_cols), (i_s % n_cols)]
        plot_data = get_plot_data(sym, start_date)
        plot_overnight_intraday_returns_linear_scale(plot_data, ax, linear_scale=linear_scale)
        ax.xaxis.set_major_locator(YearLocator(10))
        no_box(ax)
        # don't let the curves obscure the company name on the plot
        if sym == "ABMD":
            ax.set_ylim(top=1.35*ax.get_ylim()[-1])
        if sym == "ADM":
            ax.set_ylim(top=1.2*ax.get_ylim()[-1])
        # label the plot
        ax.text(0.02, 0.97, (word_wrapped_company_name(sym) + "\n" + sym),
                transform=ax.transAxes, horizontalalignment="left", verticalalignment="top", fontsize="large")
        if i_s == 0:  # show the value where the blue and green curves start at the left of the top left plot
            v = linear_scale_start_value(linear_scale)
            ax.text(plot_data.first_date - timedelta(days=120), v, str(v),
                    verticalalignment="center", horizontalalignment="right")
        ax.set_zorder(1000 - 10 * i_s)  # make doubly sure cumulative returns are not cut off

    # Add figure title and legend.
    ax = axes[0, 0]
    ax.legend(("overnight", "intraday"), loc='lower left', bbox_to_anchor=(-0.03, 1.25), fontsize="large",
              frameon=False)
    if SHOW_LEGEND_1_EQ_100_PCT and linear_scale == "fraction_of_unity":
        ax.text(0.10, 1.28, "1 = 100%", transform=ax.transAxes, verticalalignment="top")
    if linear_scale == "currency":
        fig.text(0.52, 0.91, ("Value of \$1 invested in %d Stocks in the United States S&P 500,\n"
                              "getting only overnight or intraday returns") % n_total,
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=20)
    else:
        fig.text(0.52, 0.91, "Overnight and Intraday Returns to %d Stocks in the United States S&P 500" % n_total,
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=24)
    if US_COMPANIES_50_SYMS_DATE < DEFAULT_END_DATE:
        print("Make sure US_COMPANIES_50_SYMS is up to date, and then update US_COMPANIES_50_SYMS_DATE.")
    fig.text(0.52, 0.907, ('first %d stocks ordered alphabetically by company name on %s' %
                           (n_total, US_COMPANIES_50_SYMS_DATE.strftime("%B %d, %Y"))),
             horizontalalignment="center", verticalalignment="top", transform=fig.transFigure, fontsize="small")
    fig.set_size_inches((0.12 + 4 * n_cols), (2.4 * n_rows), forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "pdf png".split():
            fn = "us_companies_50_%s.%s" % (get_date_range_str(start_date), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


def plot_overnight_intraday_returns_china_companies_50(linear_scale="fraction_of_unity"):
    """
    Make Figure 4 of "They Still Haven't Told You" (2022),
    showing overnight/intraday plots for all Chinese companies in the SSE 50 index.

    Reference:  https://www.csindex.com.cn/en/indices/index-detail/000016#/indices/family/detail?indexCode=000016

    @type linear_scale: str
    """
    assert linear_scale in LINEAR_SCALES, linear_scale
    start_date = DEFAULT_START_DATE
    clf()
    n_rows, n_cols = 10, 5
    n_total = n_rows * n_cols
    fig, axes = subplots(num=2, nrows=n_rows, ncols=n_cols, sharex=True)
    fig.subplots_adjust(wspace=0.27)  # increase the spacing between plots to accommodate some large cumulative returns
    for i_s, sym in enumerate(CHINA_SSE_50_SYMS[:n_total]):
        ax = axes[(i_s // n_cols), (i_s % n_cols)]
        s = symbol_details_dict().get(sym)
        plot_data = get_plot_data(sym, s.get("start_date", start_date))
        plot_overnight_intraday_returns_linear_scale(plot_data, ax, linear_scale=linear_scale)
        ax.xaxis.set_major_locator(YearLocator(5))
        no_box(ax)
        label_y = 0.97  # the y position of the company's name and symbol
        if sym == "600837.SS":
            label_y = 0.90  # don't obscure the cumulative intraday return to the plot to the left (600809.SS)
        # label the plot
        ax.text(0.02, label_y, (word_wrapped_company_name(sym) + "\n" + sym.replace(".SS", "")),
                transform=ax.transAxes, horizontalalignment="left", verticalalignment="top", fontsize="large")
        if i_s == 0:
            v = linear_scale_start_value(linear_scale)
            ax.text(plot_data.first_date - timedelta(days=120), v, str(v),
                    verticalalignment="center", horizontalalignment="right")
        # Put each plot in front of the plot to its right,
        # so we don't cut off the cumulative returns on the right edge of the plot
        ax.set_zorder(1000 - 10 * i_s)

    # Add figure title and legend.
    ax = axes[0, 0]
    ax.legend(("overnight", "intraday"), loc='lower left', bbox_to_anchor=(-0.03, 1.25), fontsize="large",
              frameon=False)
    if SHOW_LEGEND_1_EQ_100_PCT and linear_scale == "fraction_of_unity":
        ax.text(0.10, 1.28, "1 = 100%", transform=ax.transAxes, verticalalignment="top")
    if linear_scale == "currency":
        fig.text(0.52, 0.91, ("Value of CN$\yen 1$ invested in China's SSE 50 Stocks,\n"
                              "getting only overnight or intraday returns"),
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=20)
    else:
        fig.text(0.52, 0.91, "Overnight and Intraday Returns to China's SSE 50 Stocks",
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=24)
    if CHINA_SSE_50_SYMS_DATE < DEFAULT_END_DATE:
        print("Check to make sure the list of SSE 50 stocks is up to date, and then update CHINA_SSE_50_SYMS_DATE.")
    fig.text(0.52, 0.907, 'as of %s' % CHINA_SSE_50_SYMS_DATE.strftime("%B %d, %Y"),
             horizontalalignment="center", verticalalignment="top", transform=fig.transFigure, fontsize="small")
    fig.set_size_inches((0.12 + 4 * n_cols), (2.4 * n_rows), forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "pdf png".split():
            fn = "china_sse50_companies_%s.%s" % (get_date_range_str(start_date), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


def plot_overnight_intraday_returns_dax(linear_scale="fraction_of_unity"):
    """
    Make overnight/intraday plots for the forty constituents of Germany's DAX index.

    @type linear_scale: str
    """
    assert linear_scale in LINEAR_SCALES, linear_scale
    start_date = DEFAULT_START_DATE
    dax_syms_date = datetime(2022, 3, 31)
    clf()
    n_rows, n_cols = 8, 5
    n_total = n_rows * n_cols
    fig, axes = subplots(num=2, nrows=n_rows, ncols=n_cols, sharex=True)
    fig.subplots_adjust(wspace=0.25)  # increase the spacing between plots to accommodate some large cumulative returns
    for i_s in range(n_total)[::-1]:  # make the grid of plots in reverse order so cumulative returns are not cut off
        sym = DAX_SYMS[i_s]
        ax = axes[(i_s // n_cols), (i_s % n_cols)]
        plot_data = get_plot_data(sym, start_date)
        plot_overnight_intraday_returns_linear_scale(plot_data, ax, linear_scale=linear_scale)
        ax.xaxis.set_major_locator(YearLocator(10))
        no_box(ax)
        # don't let the curves obscure the company name on the plot
        if sym == "FME.DE":
            ax.set_ylim(top=1.35*ax.get_ylim()[-1])
        # label the plot
        ax.text(0.02, 0.97, (word_wrapped_company_name(sym) + "\n" + sym),
                transform=ax.transAxes, horizontalalignment="left", verticalalignment="top", fontsize="large")
        if i_s == 0:  # show the value where the blue and green curves start at the left of the top left plot
            v = linear_scale_start_value(linear_scale)
            ax.text(plot_data.first_date - timedelta(days=120), v, str(v),
                    verticalalignment="center", horizontalalignment="right")
        ax.set_zorder(1000 - 10 * i_s)  # make doubly sure cumulative returns are not cut off

    # Add figure title and legend.
    ax = axes[0, 0]
    ax.legend(("overnight", "intraday"), loc='lower left', bbox_to_anchor=(-0.03, 1.25), fontsize="large",
              frameon=False)
    if linear_scale == "currency":
        fig.text(0.52, 0.91, ("Value of $\euro 1$ invested in Germany's DAX stocks,\n"
                              "getting only overnight or intraday returns") % n_total,
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=20)
    else:
        fig.text(0.52, 0.91, "Overnight and Intraday Returns to Germany's DAX stocks",
                 horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize=24)
    fig.text(0.52, 0.907, ('as of %s' % dax_syms_date.strftime("%B %d, %Y")),
             horizontalalignment="center", verticalalignment="top", transform=fig.transFigure, fontsize="small")
    fig.set_size_inches((0.12 + 4 * n_cols), (2.4 * n_rows), forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "pdf png".split():
            fn = "dax_constituents_%s.%s" % (get_date_range_str(start_date), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


##############################################################################################################
# Make plots:  log scale
##############################################################################################################

def plot_overnight_intraday_returns_log_scale(plot_data, ax, currency_sym=None):
    """
    Draw a plot of cumulative returns.

    @type plot_data: PlotData
    @type ax: matplotlib.axes.Axes
    @type currency_sym: str
    """
    overnight_curve, intraday_curve = plot_data.plot_data(ax, vertical_scale="log")
    # Add yticks on the right edge of the plot.
    ytick_right_x = xlim()[0] + (xlim()[-1] - xlim()[0]) * 1.005
    todays_value_overnight = overnight_curve[-1]
    todays_value_intraday = intraday_curve[-1]
    ax.text(ytick_right_x, todays_value_overnight, " " + format_money_as_string(todays_value_overnight, currency_sym),
            verticalalignment="center")
    ax.text(ytick_right_x, todays_value_intraday, " " + format_money_as_string(todays_value_intraday, currency_sym),
            verticalalignment="center")
    # Set yticks on the left side of the plot.
    ax.set_yticks([1])
    ax.set_yticklabels([(currency_sym or "") + "1"])
    ax.tick_params(axis='y', which='minor', left=False)


def plot_overnight_intraday_returns_world_indices_log_scale(write_date_range_tex=False):
    """
    Make Figure 1 of "They Chose to Not Tell You" (2021).

    @param write_date_range_tex: If True, write date ranges to OUTPUT_PLOT_DIR/world_indices_dates.tex.
    @type write_date_range_tex: bool
    """
    clf()
    nrows, ncols = 7, 3
    fig, axes = subplots(num=1, nrows=nrows, ncols=ncols, sharex=True)
    date_range_list = []  # keep track of the date ranges for each index we plot
    for i_s, sym in enumerate(WORLD_INDICES_SYMS):
        s = symbol_details_dict().get(sym)
        ax = axes[(i_s // ncols), (i_s % ncols)]
        plot_data = get_plot_data(sym)
        plot_overnight_intraday_returns_log_scale(plot_data, ax)
        date_range_list.append(get_plot_date_range_for_inclusion_in_caption(plot_data.first_date, s))
        ax.xaxis.set_major_locator(YearLocator(5))
        no_box(ax)
        # label the plot
        short_name = s.get("short_name", s.get("name"))
        plot_label_str = s.get("country") + ("\n(%s)" % short_name if short_name else "")
        if short_name and short_name.startswith("MSCI"):
            # Adjust MSCI {Brazil,Mexico} so plot_label_str does not overlap the blue overnight curve.
            plot_label_str = short_name
        ax.text(0.50, 1.05, plot_label_str,
                transform=ax.transAxes, horizontalalignment="center", verticalalignment="top", fontsize="large")
        if i_s == 0:  # show "1" where the blue and green curves start at the left of the top left plot
            ax.text(plot_data.first_date - timedelta(days=500), 1, "1", verticalalignment="center")
    force_full_horizontal_axis(axes[0, -1])
    date_range_list = filter(None, date_range_list)

    # Add figure title and legend.
    axes[0, 0].legend(("overnight", "intraday"), loc='upper left', bbox_to_anchor=(0.00, 1.50))
    fig_title = ("Value of one unit of local currency invested in major stock market indices,\n"
                 "getting only overnight or intraday returns (logarithmic vertical scale)")
    fig.text(0.52, 0.90, fig_title,
             horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize="x-large")
    fig.set_size_inches(((5 * ncols) + 0.32), 18.5, forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "jpg png pdf".split():
            fn = "world_indices_log_%s.%s" % (get_date_range_str(), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=300)
        if write_date_range_tex:  # make footnote 10 of "They Chose to Not Tell You" (2021)
            open(os.path.join(OUTPUT_PLOT_DIR, "world_indices_dates.tex"), "w").write(
                ", ".join(date_range_list[:-1]) + ", and " + date_range_list[-1])


def plot_one_meme_stock_log_scale(sym, ax, start_date):
    """
    Plot overnight and intraday returns to the meme stock sym.

    @type sym: str
    @type ax: matplotlib.axes.Axes
    @type start_date: datetime
    """
    plot_data = get_plot_data(sym, start_date)
    plot_overnight_intraday_returns_log_scale(plot_data, ax, currency_sym="$")
    # increase the height just a little, to make sure we can see the full width of the curve near the top of the plot
    ax.set_ylim(ax.get_ylim()[0], ax.get_ylim()[1]*1.02)
    ax.xaxis.set_major_locator(YearLocator(1))
    force_full_horizontal_axis(ax, start_date)
    xticks = ax.get_xticks()
    d0 = datetime(2021, 1, 26)
    xticks[1] = date2num(d0)
    ax.set_xticks(xticks)
    # Explicitly mark January 26, 2021.
    ax.axvline(date2num(d0), 0, 0.9, color='#cccccc', linestyle='dashed', linewidth=1)
    ax.get_xticklabels()[1].set_color("gray")
    ax.set_xticklabels(["2020-01-01", "2021-01-26"])


def plot_meme_stocks_log_scale(symbols_to_plot=None):
    """
    Make Figure 6 of "They Still Haven't Told You" (2022) [and Figure 3 of "They Chose to Not Tell You" (2021)],
    showing overnight and intraday returns to the meme stocks GameStop and AMC Entertainment.

    @type symbols_to_plot: list[str]
    """
    if not symbols_to_plot:
        symbols_to_plot = "GME AMC".split()
    start_date = datetime(2020, 1, 1)
    clf()
    fig, axes = subplots(num=2, nrows=len(symbols_to_plot), ncols=1, sharex=True)
    for i_s, sym in enumerate(symbols_to_plot):
        ax = axes[i_s]
        plot_one_meme_stock_log_scale(sym, ax, start_date)
        no_box(ax, keep_yticks=True)
        s = symbol_details_dict().get(sym)
        ax.text(0.45, 0.98, s.get("short_name", s.get("name")),
                transform=ax.transAxes, horizontalalignment="center", verticalalignment="top", fontsize="large")

    # Add figure title and legend.
    axes[0].legend(("overnight", "intraday"), loc='upper left', bbox_to_anchor=(-0.07, 0.95), frameon=False)
    fig.text(0.52, 0.90, ("Value of $1 invested in a meme stock, getting only\n"
                          "overnight or intraday returns (logarithmic vertical scale)"),
             horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize="large")
    fig.set_size_inches(6, 3 * len(symbols_to_plot) + 0.5, forward=True)
    if OUTPUT_PLOT_DIR:
        for plot_format in "pdf png jpg".split():
            fn = "meme_stocks_%s.%s" % (get_date_range_str(start_date), plot_format)
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


def plot_one_sym_log_scale(sym, ax=None):
    """
    Plot the value of $1 invested in sym, getting only overnight or intraday returns, with logarithmic vertical scale.

    @type sym: str
    @type ax: matplotlib.axes.Axes
    """
    currency_sym = sym_to_currency_tex(sym)
    fig = None
    if ax is None:
        fig = figure(1)
        fig.set_size_inches(6, 6.5, forward=True)
        ax = gca()
    s = symbol_details_dict().get(sym)
    plot_data = get_plot_data(sym)
    if not plot_data:
        return
    plot_overnight_intraday_returns_log_scale(plot_data, ax, currency_sym=currency_sym)
    no_box(ax, keep_yticks=True)
    min_plot_date = datetime(s.get("start_date", plot_data.first_date).year, 1, 1)
    ax.xaxis.set_major_locator(YearLocator(5 if min_plot_date <= datetime(1995, 1, 1) else
                                           2 if min_plot_date <= datetime(2010, 1, 1) else
                                           1))
    force_full_horizontal_axis(ax, min_plot_date)
    if not fig:
        return
    # Add figure title and legend.
    ax.legend(("overnight", "intraday"), loc='upper left', bbox_to_anchor=(0.00, 1.00), frameon=False)
    fig.text(0.52, 0.90, ("Value of %s1 invested in %s (%s),\n"
                          "getting only overnight or intraday returns\n"
                          "(logarithmic vertical scale)" % ((currency_sym or ""), s.get("name"), sym)),
             horizontalalignment="center", verticalalignment="bottom", transform=fig.transFigure, fontsize="large")
    if OUTPUT_PLOT_DIR:
        start_date_str = (s.get("start_date").strftime("%Y%m%d") if s.get("start_date") else
                          DEFAULT_START_DATE.strftime("%Y%m%d") if (plot_data.first_date <
                                                                    DEFAULT_START_DATE + timedelta(10)) else
                          "IPO")
        for plot_format in "pdf png jpg".split():
            fn = ("log_%s_%s-%s.%s" %
                  (sym.split(".")[0].lower(), start_date_str, DEFAULT_END_DATE.strftime("%Y%m%d"), plot_format))
            savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight", dpi=200)


##############################################################################################################
# Make plots:  histograms
##############################################################################################################

def histogram_overnight_intraday_returns_sym(sym, sym_name, plot_data, show_detail=True):
    """
    Histogram the distribution of overnight returns and intraday returns for sym.

    @type sym: str
    @type sym_name: str
    @type plot_data: PlotData
    @param show_detail:  if True, show a properly labeled y-axis, the number of trading days, and so forth
    @type show_detail: bool
    """
    plot_data.histogram_returns()
    ax = gca()
    ax.legend(loc=2)
    if show_detail:  # show details a technically-minded person might care about
        figtext(0.135, 0.65, "bin width = 0.1%")
        figtext(0.135, 0.60, "total days = %d" % plot_data.n_days)
        ylabel("number of days per 0.1%")
    else:  # remove any lines and numbers we can
        no_box(ax)
        print("total days = %d" % plot_data.n_days)
    xlabel("return (%)")
    title("Distribution of %s overnight and intraday returns\n(%d - %d)" %
          (sym_name, plot_data.first_date.year, plot_data.last_date.year))
    if OUTPUT_PLOT_DIR:
        fn = ("overnight_intraday_return_distribution_%s_%d-%d.pdf" %
              (sym.lower(), plot_data.first_date.year, plot_data.last_date.year))
        savefig(os.path.join(OUTPUT_PLOT_DIR, fn), bbox_inches="tight")


def histogram_overnight_intraday_returns_sym_pretty(sym):
    """
    Histogram sym's overnight and intraday returns.
    With sym == "SPY", make Figure 4 of "They Chose to Not Tell You" (2021).

    @type sym: str
    """
    s = symbol_details_dict().get(sym)
    histogram_overnight_intraday_returns_sym(sym, (s.get("short_name") or s.get("name")),
                                             get_plot_data(sym), show_detail=False)


##############################################################################################################
# Make plots in articles
##############################################################################################################

def make_plots_in_article_2021():
    """Make the plots in "They Chose to Not Tell You" (2021)"""
    plot_overnight_intraday_returns_world_indices_log_scale()  # Figure 1
    plot_overnight_intraday_returns_us_companies_largest()  # Figure 2
    plot_meme_stocks_log_scale()  # Figure 3
    histogram_overnight_intraday_returns_sym_pretty("SPY")  # Figure 4


def make_plots_in_article_2022(linear_scale="fraction_of_unity"):
    """Make the plots in "They Still Haven't Told You" (2022)"""
    assert linear_scale in LINEAR_SCALES, linear_scale
    plot_overnight_intraday_returns_what_you_would_expect(linear_scale)  # Figure 1
    plot_overnight_intraday_returns_world_indices_linear_scale(linear_scale)  # Figure 2
    plot_overnight_intraday_returns_us_companies_50(linear_scale)  # Figure 3
    plot_overnight_intraday_returns_china_companies_50(linear_scale)  # Figure 4
    plot_meme_stocks_log_scale()  # Figure 6
    plot_one_sym_log_scale("3333.HK")  # Figure 7


if __name__ == "__main__":
    make_plots_in_article_2022()
