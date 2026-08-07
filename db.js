require('dotenv').config();
const { Pool } = require('pg');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

async function setupDatabase() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS telegram_users (
        id SERIAL PRIMARY KEY,
        chat_id BIGINT UNIQUE NOT NULL,
        username VARCHAR(100),
        first_name VARCHAR(100),
        mmhr_email VARCHAR(150),
        mmhr_password VARCHAR(100),
        mmhr_token TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      );
    `);
    await pool.query(`ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS mmhr_email VARCHAR(150);`);
    await pool.query(`ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS mmhr_password VARCHAR(100);`);
    await pool.query(`ALTER TABLE telegram_users ADD COLUMN IF NOT EXISTS mmhr_token TEXT;`);
    console.log('✅ تم التأكد من وجود جدول telegram_users');
  } catch (err) {
    console.error('❌ خطأ أثناء إعداد قاعدة البيانات:', err.message);
  }
}

async function saveUser(chatId, username, firstName) {
  try {
    await pool.query(
      `INSERT INTO telegram_users (chat_id, username, first_name)
       VALUES ($1, $2, $3)
       ON CONFLICT (chat_id) DO UPDATE
       SET username = EXCLUDED.username, first_name = EXCLUDED.first_name`,
      [chatId, username, firstName]
    );
  } catch (err) {
    console.error('❌ خطأ أثناء حفظ المستخدم:', err.message);
  }
}

async function getUser(chatId) {
  const result = await pool.query('SELECT * FROM telegram_users WHERE chat_id = $1', [chatId]);
  return result.rows[0] || null;
}

async function saveMmhrAccount(chatId, email, password, token) {
  await pool.query(
    `UPDATE telegram_users SET mmhr_email = $1, mmhr_password = $2, mmhr_token = $3 WHERE chat_id = $4`,
    [email, password, token, chatId]
  );
}

async function updateMmhrToken(chatId, token) {
  await pool.query(`UPDATE telegram_users SET mmhr_token = $1 WHERE chat_id = $2`, [token, chatId]);
}

module.exports = { pool, setupDatabase, saveUser, getUser, saveMmhrAccount, updateMmhrToken };
