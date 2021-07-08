import os
import gzip
import json
from yieldenv.constants import CONTRACT_DATA, DATA_PATH
import pandas as pd
import matplotlib.pyplot as plt

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
    APY_CALC_PERIOD_POOL = 7  # days

    pps_df['return'] = ((pps_df['Price Per Share'].values - pps_df['Price Per Share'].shift(maturity_in_days).values)) \
                       / pps_df['Price Per Share'].values

    pps_df['Yearn APY'] = ((pps_df['Price Per Share'].values - pps_df['Price Per Share'].shift(APY_CALC_PERIOD_YEARN).values)) \
                       / pps_df['Price Per Share'].values

    pps_df['Yearn APY'] = (1 + pps_df['Yearn APY']).pow(365 / APY_CALC_PERIOD_YEARN) - 1

    pps_df['Naive Fixed Rate'] = (pps_df['Yearn APY'] - naive_fixed_rate_discount) / (365 / maturity_in_days)

    pps_df['Price of 1 pDAI'] = 1 / (1 + pps_df['Naive Fixed Rate'])

    pps_df['Share of Pool in YTC'] = (yearn_exposure_multiplier - pps_df['Price of 1 pDAI']*yearn_exposure_multiplier - 1 + pps_df['Price of 1 pDAI']) / pps_df['Price of 1 pDAI']

    pps_df['YT Balance with 1DAI'] = pps_df['Share of Pool in YTC'] / (1-pps_df['Price of 1 pDAI'])

    pps_df['yvDAI Balance with 1DAI'] = 1 - pps_df['Share of Pool in YTC']

    pps_df = pps_df.dropna()

    pps_df = pps_df.iloc[::maturity_in_days, :]

    pps_df['Payoff'] = pps_df['YT Balance with 1DAI'].shift(1) * pps_df['return'] + pps_df['YT Balance with 1DAI'].shift(1)*(1+pps_df['return'])

    pps_df['Payoff'][0] = 1.0

    pps_df['Pool Price Per Share'] = pps_df['Payoff'].cumprod()

    pps_df['Pool APY Since Inception'] = pps_df['Pool Price Per Share'].pow(365 / (pps_df.index - pps_df.index[0]).days) - 1

    pps_df['Pool Return'] = ((pps_df['Pool Price Per Share'].values - pps_df['Pool Price Per Share'].shift(int(APY_CALC_PERIOD_YEARN/APY_CALC_PERIOD_POOL)).values)) \
                       / pps_df['Price Per Share'].values

    pps_df['Pool Excess Return'] = pps_df['Pool Return'] - pps_df['return']

    strategy_apy = pps_df['Pool APY Since Inception'][-1]
    strategy_return = pps_df['Pool Price Per Share'][-1] - 1
    yearn_return = (pps_df['Price Per Share'][-1] - pps_df['Price Per Share'][0]) / pps_df['Price Per Share'][0]

    pps_df = pps_df.dropna()

    std_strategy_excess_returns = pps_df['Pool Excess Return'].std()
    sharpe_ratio = (strategy_return - yearn_return) / (std_strategy_excess_returns)

    average_share_of_ytc = pps_df['Share of Pool in YTC'].mean()

    std_strategy_returns = pps_df['Pool Return'].std()

    # return {"Strategy APY": strategy_apy, "Sharpe Ratio": sharpe_ratio, "Strategy Return": strategy_return,
    #         "Yearn Return": yearn_return, "Excess Returns Standard Deviation": std_strategy_excess_returns,
    #         "Average Share of Pool In YTC": average_share_of_ytc}

    return {"Strategy APY": strategy_apy, "Standard Deviation of Returns": std_strategy_returns,
            "Average Share of Pool In YTC": average_share_of_ytc}


# multipliers = [5, 50, 100, 150, 200, 300, 400]
multipliers_dict = {}

for multiplier in range(199, 201, 1):
    multipliers_dict[multiplier] = compute_ytc_strategy_return(pps_df=df, yearn_exposure_multiplier=multiplier, maturity_in_days=7, naive_fixed_rate_discount=0.0175)

multipliers_df = pd.DataFrame.from_dict(data=multipliers_dict, orient='index')


def create_plots(df):

    for i, col in enumerate(df.columns):
        df[col].plot(fig=plt.figure(i))
        plt.title(col)

    plt.show()


# create_plots(df=multipliers_df)
print('done')










