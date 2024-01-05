#!/usr/bin/env python3
'''
Stefan Lohmaier <stefan@slohmaier.de>, hereby disclaims all copyright interest in the program “mintoscsv2parqetcsv” (which deconstructs trees) written by James Hacker.
---
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.
'''
import argparse
import csv
import os
import re
import sys

class Transaction:
    def __init__(self, date, time, amount):
        self.date = date
        self.time = time
        self.amount = amount

class Transactions:
    def __init__(self):
        self.withdrawals = []
        self.interests = []
        self.deposits = []
        self.taxes = []
        self.withdrawals = []

REGEX_HOLDING_URL = re.compile(r'https://app\.parqet\.com/p/\w+/h/(?P<holdingid>\w+)')
REGEX_LOAN = re.compile(r'.*\(Loan (?P<loanid>\S+)\).*')

def parse_amount(amount: str):
    return '{:.6f}'.format(float(amount))

if __name__ == '__main__':
    argparser = argparse.ArgumentParser('mintoscsv2parqetcsv',
        description='Convert Mintos Statement CSV\'s to Parqet CSV\'s.')
    argparser.add_argument('--mcsv', '-m', dest='mcsv', required=True,
        help='path to Mintos Statement CSV')
    argparser.add_argument('--pcsv', '-p', dest='pcsv', required=True,
        help='output path for Parqet Cash CSV')
    argparser.add_argument('--hurl', '-u', dest='hurl', required=True,
        help='Link to the Holding in Parqet https://app.parqet.com/p/[PORTFOLIOID]/h/[HOLDING-ID]')

    args = argparser.parse_args()
    #fod code completion
    args.mcsv = args.mcsv
    args.pcsv = args.pcsv
    args.hurl = args.hurl
    
    if not os.path.isfile(args.mcsv):
        sys.stderr.write('Mintos CSV "{0}" is not a file! Try {1} -h.\n'
            .format(args.mcsv, sys.argv[0]))
        sys.exit(1)
    match = REGEX_HOLDING_URL.match(args.hurl)
    if match is None:
        sys.stderr.write('Holding Url "{0}" does not match the pattern! Try {1} -h.\n'
            .format(args.hurl, sys.argv[0]))
        sys.exit(1)
    holdingId = match.group('holdingid')
    
    mcsvFile = open(args.mcsv, 'r')
    mcsv = csv.reader(mcsvFile)

    transactions = {}
    for row in mcsv:
        cDate = None
        cTime = None
        if row[0].find(' ') != -1:
            cDate, cTime = row[0].split(' ', 1) 
        if cDate is None or cTime is None:
            continue

        cFee = '0'
        cType = ''
        cAmount = '0'
        cTax = '0'
        cHolding = holdingId
        cAmount = parse_amount(row[-4])
        match = REGEX_LOAN.match(row[2])
        if match:
            cLoan = match.group('loanid')
        else:
            cLoan = row[2]
        if not cLoan in transactions:
            transactions[cLoan] = Transactions()
        transaction = Transaction(cDate, cTime, cAmount)

        if row[-1] == 'Deposits':
            transactions[cLoan].deposits.append(transaction)
        elif row[-1] == 'Interest received':
            transactions[cLoan].interests.append(transaction)
        elif row[-1] == 'Tax withholding':
            transactions[cLoan].interests.append(transaction)
        elif row[-1] == 'Withdrawal':
            if transaction.amount.startswith('-'):
                transaction.amount = transaction.amount[1:]
            transactions[cLoan].withdrawals.append(transaction)

    rows = []
    for loan in transactions:
        t = transactions[loan]
        for deposit in t.deposits:
            rows.append([deposit.date, deposit.time, deposit.amount, '0', '0', 'TransferIn', holdingId])
        for withdrawal in t.withdrawals:
            rows.append([withdrawal.date, withdrawal.time, withdrawal.amount, '0', '0', 'TransferOut', holdingId])
        for interest in t.interests:
            if float(interest.amount) == 0.0:
                continue
            rows.append([
                interest.date,
                interest.time,
                interest.amount,
                '0',
                '0', 'Interest', holdingId])

    pcsvFile = open(args.pcsv, 'w+')
    pcsv = csv.writer(pcsvFile, 'unix', quoting=0, delimiter=';')
    pcsv.writerow(['date', 'time', 'amount', 'tax', 'fee', 'type', 'holding'])

    def rowSorter(row):
        return row[0] + row[1]
    rows.sort(key=rowSorter)
    for row in rows:
        pcsv.writerow(row)

    mcsvFile.close()
    pcsvFile.close()
