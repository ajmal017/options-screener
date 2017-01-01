from pandas_datareader.data import Options
import requests_cache
import datetime

#####################################################################
# Settings

# tickers to fetch data for
tickers = ['AAPL', 'GOOG', 'AMZN', 'MSFT', 'SPY', 'FB', 'QQQ']

# output file name
outfile = 'covered_calls.csv'

# cache settings
days_to_cache = 1

# CSV columns to export
csv_cols = [
    'xProfitCurAnnual%',
    'xInsurance%',
    'xProfitMaxAnnual%',
    'xDaysUntilExpiration',
    'Root',
    'Underlying_Price',
    'Strike',
    'Type',
    'Expiry',
    'Symbol',
    'Bid',
    'Vol',
    'Open_Int',
    'IV',
]

# CSV columns to sort by
sort_cols = ['xProfitCurAnnual%', 'xInsurance%', 'xProfitMaxAnnual%']

#####################################################################
# Functions


def covered_call_csv_out(filename, df):
    # calls
    # not expired
    # out of the money
    # greater than 2 weeks from expiration
    # volume greater than 1
    # open interest greater than 10
    filtered = df.loc[(df['Type'] == 'calls') & (df[
        'xExpired'] is not True) & (df['Strike'] > df['Underlying_Price']) & (
            df['xDaysUntilExpiration'] >= 14) & (df['Vol'] > 1) & (df[
                'Open_Int'] > 10)]

    ret = filtered.sort_values(
        by=sort_cols, ascending=False).to_csv(
            filename, columns=csv_cols, index=False, float_format='%.2f')
    return ret


def covered_call_process_dataframe(df):
    # reset_index()
    #   copies multi-index values into columns
    #   sets index to single ordinal integer
    df.reset_index(inplace=True)

    # calculate other values
    #  The bid price is a conservative estimate of the current option price
    df['xDaysUntilExpiration'] = df.apply(
        lambda row: (row['Expiry'].to_pydatetime() - today).days, axis=1)
    df['xExpired'] = df.apply(
        lambda row: row['xDaysUntilExpiration'] <= 0, axis=1)
    df['xInsurance%'] = df.apply(
        lambda row: 100.0 * row['Bid'] / row['Underlying_Price'], axis=1)
    df['xProfitCur'] = df.apply(lambda row: row['Bid'], axis=1)
    df['xProfitCur%'] = df.apply(
        lambda row: 100.0 * row['Bid'] / row['Underlying_Price'], axis=1)
    df['xProfitCurAnnual%'] = df.apply(
        lambda row: row['xProfitCur%'] * 365.0 / row['xDaysUntilExpiration'],
        axis=1)
    df['xProfitMax'] = df.apply(
        lambda row: row['Bid'] + row['Strike'] - row['Underlying_Price'],
        axis=1)
    df['xProfitMax%'] = df.apply(
        lambda row: 100.0 * row['xProfitMax'] / row['Underlying_Price'],
        axis=1)
    df['xProfitMaxAnnual%'] = df.apply(
        lambda row: row['xProfitMax%'] * 365.0 / row['xDaysUntilExpiration'],
        axis=1)
    df['xPriceLossAt'] = df.apply(
        lambda row: row['Underlying_Price'] - row['Bid'], axis=1)

    return df


#####################################################################
# Main

# use cache to reduce web traffic
session = requests_cache.CachedSession(
    cache_name='cache',
    backend='sqlite',
    expire_after=datetime.timedelta(days=days_to_cache))

today = datetime.datetime.today()

# all data will also be combined into one CSV
all_df = None

for ticker in tickers:
    option = Options(ticker, 'yahoo', session=session)

    # fetch all data
    df = option.get_all_data()

    # covered_call_csv_out
    df = covered_call_process_dataframe(df)

    # ensure the all_df (contains all data from all tickers)
    if all_df is None:
        all_df = df.copy(deep=True)
    else:
        all_df = all_df.append(df)

# output the all_df, which contains all of the tickers
covered_call_csv_out(outfile, all_df)
