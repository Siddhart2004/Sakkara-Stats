#!/usr/bin/env python3
"""
Database migration script to add name column to User table
"""

import sqlite3
import os

# Database path
db_path = 'instance/sakkara_stats.db'

def migrate_database():
    if not os.path.exists(db_path):
        print("Database does not exist yet. It will be created when the app runs.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if name column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'name' not in columns:
            print("Adding 'name' column to user table...")
            cursor.execute("ALTER TABLE user ADD COLUMN name VARCHAR(100)")
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("Name column already exists. No migration needed.")
        
        conn.close()
        
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate_database()