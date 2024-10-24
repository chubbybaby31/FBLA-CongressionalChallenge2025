import React, { useState, useEffect } from 'react';
import './App.css';
import '@fortawesome/fontawesome-free/css/all.min.css';

interface Transaction {
  amount: number;
  description: string;
  type: 'income' | 'expense';
  date: string;
}

interface FinancialData {
  currentBalance: number;
  monthlyIncome: number;
  monthlyExpense: number;
  transactions: Transaction[];
}

const App: React.FC = () => {
  const [financialData, setFinancialData] = useState<FinancialData>({
    currentBalance: 0,
    monthlyIncome: 0,
    monthlyExpense: 0,
    transactions: []
  });

  const [newAmount, setNewAmount] = useState<string>('');
  const [newDescription, setNewDescription] = useState<string>('');
  const [transactionType, setTransactionType] = useState<'income' | 'expense'>('expense');

  useEffect(() => {
    fetchFinancialData();
  }, []);

  const fetchFinancialData = async () => {
    try {
      const response = await fetch('http://localhost:3001/api/financial-data');
      const data = await response.json();
      setFinancialData(data);
    } catch (error) {
      console.error('Error fetching financial data:', error);
    }
  };

  const addTransaction = async () => {
    if (!newAmount || !newDescription) {
      alert('Please enter both amount and description');
      return;
    }

    try {
      const response = await fetch('http://localhost:3001/api/add-transaction', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: parseFloat(newAmount),
          description: newDescription,
          type: transactionType
        })
      });
      const data = await response.json();
      if (data.success) {
        setFinancialData(prevData => ({
          ...prevData,
          currentBalance: data.newBalance,
          transactions: [...prevData.transactions, data.transaction]
        }));
        setNewAmount('');
        setNewDescription('');
      }
    } catch (error) {
      console.error('Error adding transaction:', error);
    }
  };

  const viewTransactions = () => {
    // For now, we'll just log the transactions. In a real app, you might want to show these in a modal or a new page.
    console.log(financialData.transactions);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Personal Finance Manager</h1>
      </header>
      <main>
        <section className="balance-section">
          <h2>Current Balance</h2>
          <p className="balance">${financialData.currentBalance.toFixed(2)}</p>
        </section>
        <section className="monthly-summary">
          <div className="summary-item income">
            <i className="fas fa-money-bill-wave"></i>
            <h3>Monthly Income</h3>
            <p>${financialData.monthlyIncome.toFixed(2)}</p>
          </div>
          <div className="summary-item expenses">
            <i className="fas fa-credit-card"></i>
            <h3>Monthly Expenses</h3>
            <p>${financialData.monthlyExpense.toFixed(2)}</p>
          </div>
        </section>
        <section className="actions-section">
          <div>
            <input 
              type="number" 
              value={newAmount} 
              onChange={(e) => setNewAmount(e.target.value)} 
              placeholder="Amount"
            />
            <input 
              type="text" 
              value={newDescription} 
              onChange={(e) => setNewDescription(e.target.value)} 
              placeholder="Description"
            />
            <select value={transactionType} onChange={(e) => setTransactionType(e.target.value as 'income' | 'expense')}>
              <option value="expense">Expense</option>
              <option value="income">Income</option>
            </select>
            <button className="action-button" onClick={addTransaction}>Add Transaction</button>
          </div>
          <button className="action-button secondary" onClick={viewTransactions}>View Transactions</button>
        </section>
        <footer className="footer-gradient">
          <h2>Stay on Track with Your Finances!</h2>
        </footer>
      </main>
    </div>
  );
}

export default App;