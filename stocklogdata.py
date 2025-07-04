import os
import pandas as pd


class StockLogData:
    def __init__(self, folder_path: str):
        """
        Initialize the StockLogData with the provided data.

        :param data: DataFrame containing stock log data.
        """
        self.folder_path = folder_path
        
        # Check if the folder exists
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"The folder {folder_path} does not exist.")
    
    def get_week_list(self):
        """
        Get a list of weeks from the folder names in the specified folder path.

        :return: List of week names.
        """
        week_list = []
        
        # Iterate through the folder names in the specified path
        for folder_name in os.listdir(self.folder_path):
            folder_path = os.path.join(self.folder_path, folder_name)
            if os.path.isdir(folder_path):
                week_list.append(folder_name)

        # The folder is in the format "YYYY-MM-DD", so we can sort it
        week_list.sort(key=lambda x: x.split('-'))
        return week_list
    
    def find_day_stats(self):
        """
        Find the day statistics from the folder names in the specified folder path.

        :return: List of day statistics.
        """
        day_stats = []
        trade_stats = pd.DataFrame(columns=['Date', 'entry_time', 'exit_time', 'trade_type', 'entry_price', 'exit_price', 'profit_loss', 'max_drawdown', 'max_drawup'])
        week_list = self.get_week_list()

        # Within each week folder, look for "metadata.csv" file that contains a dataframe with stock data
        for week in week_list:
            week_path = os.path.join(self.folder_path, week)
            metadata_file = os.path.join(week_path, "metadata.csv")
            if os.path.exists(metadata_file):
                # Read the metadata file as a DataFrame
                metadata_df = pd.read_csv(metadata_file)

                # Contains a column "Time" which is in the format "YYYY-MM-DD HH:MM"
                # Get the Date and Time from the "Time" column
                metadata_df['Date'] = pd.to_datetime(metadata_df['Time']).dt.date
                metadata_df['Time'] = pd.to_datetime(metadata_df['Time']).dt.time

                # Group by Date
                # Get the column with "AI Recommendation" that can contain "open_long", "open_short", "close_long", "close_short"
                # Count the occurrences of each recommendation type using contains as the column can contain multiple values with commas
                # trade_count is the total number of trades for the day or sum of open_long, open_short, close_long, close_short
                day_grouped = metadata_df.groupby('Date').agg(
                    trade_count=('AI Recommendation', lambda x: x.str.contains('open_long|open_short|close_long|close_short').sum()),
                    open_long_count=('AI Recommendation', lambda x: x.str.contains('open_long').sum()),
                    open_short_count=('AI Recommendation', lambda x: x.str.contains('open_short').sum()),
                    close_long_count=('AI Recommendation', lambda x: x.str.contains('close_long').sum()),
                    close_short_count=('AI Recommendation', lambda x: x.str.contains('close_short').sum()),
                ).reset_index()

                # To do the trade statistics, look through each row in the date grouped DataFrame
                # Whenever a row has an "AI Recommendation" string that contains "open_long" or "open_short", it is an entry trade and the Stock Price is the entry price
                # Whenever a row has an "AI Recommendation" string that contains "close_long" or "close_short", it is an exit trade and the Stock Price is the exit price
                # If the AI recommendation does not contain "close_long" or "close_short" within the same date, then consider the last trade of the day as the exit trade for the entry trade
                # Read the "Stock Price" column between the entry and exit trades to calculate the profit/loss, max drawdown, and max drawup
                # Implement this by iterating through each date and each row in the date grouped DataFrame
                for date, group in metadata_df.groupby('Date'):
                    entry_trade = None
                    entry_idx = None
                    for index, row in group.iterrows():
                        if 'open_long' in row['AI Recommendation'] or 'open_short' in row['AI Recommendation']:
                            # This is an entry trade
                            entry_trade = {
                                'Date': date,
                                'entry_time': row['Time'],
                                'trade_type': "long" if 'open_long' in row['AI Recommendation'] else "short",
                                'entry_price': row['Stock Price']
                            }
                            entry_idx = index
                        elif 'close_long' in row['AI Recommendation'] or 'close_short' in row['AI Recommendation']:
                            # This is an exit trade
                            if entry_trade is not None and entry_idx is not None:
                                exit_trade = {
                                    'exit_time': row['Time'],
                                    'exit_price': row['Stock Price']
                                }
                                # Get the price series between entry and exit (inclusive)
                                price_series = group.loc[entry_idx:index, 'Stock Price']
                                entry_price = entry_trade['entry_price']
                                # If trade_type is long, profit_loss is exit_price - entry_price
                                # If trade_type is short, profit_loss is entry_price - exit_price
                                if entry_trade['trade_type'] == "long":
                                    profit_loss = exit_trade['exit_price'] - entry_price
                                    max_drawdown = price_series.min() - entry_price
                                    max_drawup = price_series.max() - entry_price

                                else:
                                    profit_loss = entry_price - exit_trade['exit_price']
                                    max_drawdown = entry_price - price_series.max()
                                    max_drawup = entry_price - price_series.min()

                                # Append the trade statistics to the trade_stats DataFrame
                                trade_stats = pd.concat([
                                    trade_stats,
                                    pd.DataFrame([{
                                        **entry_trade,
                                        **exit_trade,
                                        'profit_loss': profit_loss,
                                        'max_drawdown': max_drawdown,
                                        'max_drawup': max_drawup
                                    }])
                                ], ignore_index=True)

                                # Reset the entry trade after processing
                                entry_trade = None
                                entry_idx = None

                    # If there was an entry trade but no close trade found, use the last row as the exit trade
                    if entry_trade is not None and entry_idx is not None:
                        last_row = group.iloc[-1]
                        exit_trade = {
                            'exit_time': last_row['Time'],
                            'exit_price': last_row['Stock Price']
                        }
                        price_series = group.loc[entry_idx:last_row.name, 'Stock Price']
                        entry_price = entry_trade['entry_price']
                        if entry_trade['trade_type'] == "long":
                            profit_loss = exit_trade['exit_price'] - entry_price
                            max_drawdown = price_series.min() - entry_price
                            max_drawup = price_series.max() - entry_price
                        else:
                            profit_loss = entry_price - exit_trade['exit_price']
                            max_drawdown = entry_price - price_series.max()
                            max_drawup = entry_price - price_series.min()

                        trade_stats = pd.concat([
                            trade_stats,
                            pd.DataFrame([{
                                **entry_trade,
                                **exit_trade,
                                'profit_loss': profit_loss,
                                'max_drawdown': max_drawdown,
                                'max_drawup': max_drawup
                            }])
                        ], ignore_index=True)

                # Find the day profit/loss, max drawdown, and max drawup for each date using the trade_stats DataFrame
                day_grouped['day_profit_loss'] = day_grouped['Date'].map(
                    trade_stats.groupby('Date')['profit_loss'].sum()
                )
                day_grouped['day_max_drawdown'] = day_grouped['Date'].map(
                    trade_stats.groupby('Date')['max_drawdown'].min()
                )
                day_grouped['day_max_drawup'] = day_grouped['Date'].map(
                    trade_stats.groupby('Date')['max_drawup'].max()
                )

                # Append the day statistics to the day_stats DataFrame
                day_stats.append(day_grouped)
        
        day_stats = pd.concat(day_stats, ignore_index=True)
        return day_stats, trade_stats

    def get_day_data(self, date: str):
        """
        Get the day data for a specific date.

        :param date: The date in the format "YYYY-MM-DD".
        :return: DataFrame containing the day data.
        """

        week_list = self.get_week_list()

        # find the date (YYYY-MM-DD) is present between which weeks
        for week in week_list:
            week_path = os.path.join(self.folder_path, week)
            metadata_file = os.path.join(week_path, "metadata.csv")
            if os.path.exists(metadata_file):
                # Read the metadata file as a DataFrame
                metadata_df = pd.read_csv(metadata_file)

                # Contains a column "Time" which is in the format "YYYY-MM-DD HH:MM"
                # Get the Date and Time from the "Time" column
                metadata_df['Date'] = pd.to_datetime(metadata_df['Time']).dt.date
                metadata_df['Time'] = pd.to_datetime(metadata_df['Time']).dt.time

                # Convert the Date to list of dates string format
                dates_list_string = metadata_df['Date'].astype(str).unique().tolist()
                # Check if the date is present in the metadata_df
                if date in dates_list_string:
                    # Filter the DataFrame for the specific date in its own format
                    day_data = metadata_df[metadata_df['Date'] == pd.to_datetime(date).date()]
                    # Reset the index of the DataFrame
                    day_data.reset_index(drop=True, inplace=True)
                    # Return the day data and the week path
                    return day_data, week_path
        
        return None, None