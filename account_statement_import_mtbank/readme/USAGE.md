To import a bank statement:

1. Go to **Accounting > Dashboard**
2. Click on the **Import** button on your bank journal
3. Select the MTBank XML file downloaded from your online banking
4. Click **Import**

The module will automatically:
* Detect the MTBank XML format
* Extract the account number and currency
* Create bank statement(s) with transactions
* Match the journal based on the bank account number

**Note:** The MTBank XML format contains daily summaries with debit/credit turnover totals rather than individual transaction details. The import will create aggregated transaction lines for each day with movements.

**Requirements:**
* Bank journal must be configured with the correct Belarus IBAN account number
* The `l10n_by` and `l10n_by_bank` modules must be installed for Belarus account validation
