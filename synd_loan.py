"""
Syndicated Loan
"""
import pandas as pd
from pandas.tseries.frequencies import to_offset
import numpy as np
from datetime import date
from typing import Union

Number = Union[int, float, np.int, np.float]
M = 10**6
DAYSINYEAR = 360

def dailyInterest(notional: Number, interest: Number, start: date, end: date):
    delta = (end-start).days
    return notional * interest * delta    

class SyndLoan:
    def __init__(self, **kwargs
#        crdLine,
#        closeDate,	
#        minDrawDown,	#5
#        drawDownIncr,	#1	
#        repaymentPeriods,
#        repaymentFreq,        
#        #optionals
#        agreement_date,	

#Availability Period	12
#Extension of Availability?	6
#Tenor/Final Maturity 	36
#Final Availability (Mths from Start)	18
#Final Repayment (Mths from Start)	54
#Margin	0.95%
#Rate	L + 0.95%
#	
#Drawdown	
#
#Max Loans Outstanding	10
#Commitment Fees - Rate	0.25%
#Commitment Fees - Period	7
#	
#Arrangement Fee	1%
#	
#Repayment	12
#	8.33%
#schedule	3
#first instalment due	3
#	
#Default Interest	1%
#	
#Voluntary Prepayment	
#Min	3
#Min Increments	1
#	
            
    ):
        self.__dict__ = kwargs
        self.drawDowns = pd.Series()
        self.repayments = pd.Series()
        # TODO parse commitments
    
    def check(self, condition: bool, msg: str=''):
        if not self.whatif:
            assert condition, msg
    
    @property
    def drawn(self):    
        return sum(self.drawDowns)
    
    @property
    def repaid(self):    
        return sum(self.repayments)
        
    @property
    def undrawn(self):
        return self.crdLine + self.repaid - self.drawn    
        
    def _checkDrawDown(self, amt:int):
        assert amt >= self.minDrawDown 
        assert amt % self.drawDownIncr == 0
        self.check(amt < self.undrawn) 
    
    def repay(self, amt:int, date_:date=None):
        """
        TODO: add checking for early repayment  
        """
        self.repayments.set_value(np.datetime64(date_), amt)
    
    def drawDown(self, amt:int, date_:date=None):
        """
        TODO: this needs to be persisted
        """
        date_ = date_ or date.today()
        self.check(date_ >= date.today()) #TODO do we need this?
        self._checkDrawDown(amt)
        
        #persist this
        self.drawDowns.set_value(np.datetime64(date_), amt)
    
    def _repaymentSchedule(self, amt:int, drawDownDate:date): 
        series = pd.Series(
            amt/self.repaymentPeriods, 
            pd.date_range(drawDownDate, 
                periods=self.repaymentPeriods + 1, 
                freq=self.repaymentFreq
            )[1:]
        )
        return series
    
    @property
    def repaymentSchedule(self):         
        payments = list(map(lambda x: self._repaymentSchedule(*x),
           zip(self.drawDowns, self.drawDowns.index)
        ))
        result = pd.concat(payments)
        return result
    
    @property
    def cashflows(self):    
        raw = pd.concat([
            self.drawDowns,
            -self.repaymentSchedule,
        ]).sort_index()
        df = pd.DataFrame(raw, columns=['transaction'])
        df['undrawn'] = self.crdLine - raw.cumsum()
        return df        
    

    def _commitmentSchedule(self):
        cf = self.cashflows
        df = cf.groupby(cf.index)['undrawn'].last()  
        rsm = df.resample('1MS').pad()
        start = rsm.index[0] + to_offset(self.commitmentStart) #TODO: parse this in init
        end = rsm.index[0] + to_offset(self.commitmentEnd) #TODO: parse this in init
        rsmFiltered = rsm.loc[start:end] * self.commitmentInterest / DAYSINYEAR
        rsmdaily = rsmFiltered.asfreq('D', method='ffill')
        return rsmdaily 
        
    @property
    def commitmentSchedule(self):
        raw = self._commitmentSchedule()
        result = raw.resample('MS').sum() 
        return result
        
def example():
    self = SyndLoan(**dict(
        crdLine=290*M,
        closeDate=date(2020,1,1),	
        minDrawDown=5*M,	#5
        drawDownIncr=1*M,	#1	
        repaymentPeriods=12,
        repaymentFreq='3MS',  
        commitmentStart='7MS', # can be months
        commitmentEnd='18MS', # can be months
        commitmentInterest=0.0025,
        
        #optional           
        whatif=True
    ))
    self.drawDown(50*M, date(2020, 1, 1))
    self.drawDown(80*M, date(2020, 4, 1))
    self.drawDown(80*M, date(2020, 6, 1))
    self.drawDown(70*M, date(2020, 9, 1))
    
#    self.repay(100*M, date(2021, 1, 1)) #hack cumulative repayment
    
    self.drawDown(60*M, date(2021, 1, 1))
    self.drawDown(5*M, date(2021, 2, 1))
    self.drawDown(5*M, date(2021, 4, 1))
    
 #   self.repay(200*M, date(2021, 1, 1)) #hack cumulative repayment
     
    self.drawDown(52*M, date(2021, 7, 1))
    
    cumsum = self.cashflows.sort_index()
    
    
    self.drawDown(20, date(2020, 2, 1))
    self.drawDown(20, date(2020, 2, 1))

"""
1. what is the divide by 4 in interest calculations? at first I Thought it was per quarter but those calculations happen monthly.
2. commitment interest based on contractual schedule or actual funding reserves? e.g. what if borrower misses repayment?
3. how is penalty interest incurred
a) grace period?
b) on entire notional or just that repayment? one off or time based?
c) if partial payemnt?

4. how do we currently model multiple cashs flows on same day? fees, vs interest vs repayment order of priority? unautheorized overpayments?
5. do clients explicitly mention what each payment is for?
"""
