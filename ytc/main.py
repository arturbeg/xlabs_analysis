import os
import gzip
import json
from yieldenv.constants import CONTRACT_DATA, DATA_PATH
import pandas as pd

BLOCK_NUMBER = "blocks"
VALUE = "pps"

# TODO: determine appropriate fixed rate depending on the maturity
# TODO: risk measures

CONTRACT_DATA = CONTRACT_DATA['DAI yVault']

result = {BLOCK_NUMBER: [], VALUE: []}
with gzip.open(
    os.path.join(
        DATA_PATH, f"yearn_DAI_price_per_share.jsonl.gz"
    )
) as f:
    for _, w in enumerate(f):
        this_block = json.loads(w)
        if this_block[1] / 1e18 > 0.1:
            result[BLOCK_NUMBER].append(this_block[0])
            result[VALUE].append(this_block[1] / (10**int(CONTRACT_DATA["decimals"])))
    date_range = pd.date_range(CONTRACT_DATA["start_date"], CONTRACT_DATA["end_date"], periods=len(result[BLOCK_NUMBER]))


df = pd.DataFrame(data=result[VALUE], index=date_range, columns=['Price Per Share'])

# sample approximately every day
df = df.iloc[::13, :]


def compute_ytc_strategy_return(pps_df, yearn_exposure_multiplier, maturity_in_days, naive_fixed_rate_discount=0.02):

    APY_CALC_PERIOD_YEARN = 7 # days

    pps_df['return'] = ((pps_df['Price Per Share'].values - pps_df['Price Per Share'].shift(maturity_in_days).values)) \
                       / pps_df['Price Per Share'].values

    pps_df['Yearn APY'] = ((pps_df['Price Per Share'].values - pps_df['Price Per Share'].shift(APY_CALC_PERIOD_YEARN).values)) \
                       / pps_df['Price Per Share'].values

    pps_df['Yearn APY'] = (1 + pps_df['Yearn APY']).pow(365 / APY_CALC_PERIOD_YEARN) - 1

    pps_df['Naive Fixed Rate'] = (pps_df['Yearn APY'] - naive_fixed_rate_discount) / (365 / maturity_in_days)

    pps_df['Price of 1 pDAI'] = 1 / (1 + pps_df['Naive Fixed Rate'])

    pps_df['Share of Pool in YTC'] = (yearn_exposure_multiplier - pps_df['Price of 1 pDAI']*yearn_exposure_multiplier - 1 + pps_df['Price of 1 pDAI']) / pps_df['Price of 1 pDAI']

    pps_df['YT Balance'] = pps_df['Share of Pool in YTC'] / (1-pps_df['Price of 1 pDAI'])

    pps_df['yvDAI Balance'] = 1 - pps_df['Share of Pool in YTC']

    pps_df = pps_df.dropna()

    # payoffs = {}

    pps_df = pps_df.iloc[::maturity_in_days, :]

    pps_df['Payoff'] = pps_df['YT Balance'].shift(1) * pps_df['return'] + pps_df['yvDAI Balance'].shift(1)*(1+pps_df['return'])

    pps_df['Cumulative Payoff'] = pps_df['Payoff'].cumprod()

    pps_df['Pool APY'] = pps_df['Cumulative Payoff'].pow(365 / (pps_df.index - pps_df.index[0]).days) - 1

    return pps_df


compute_ytc_strategy_return(pps_df=df, yearn_exposure_multiplier=10, maturity_in_days=7)














