#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ BiP Bot - SQLite Veritabanı Modülü
Profesyonel veritabanı işlemleri için modül

Özellikler:
- ACID uyumlu SQLite veritabanı
- İlişkisel veri modeli
- Foreign key kısıtlamaları
- Otomatik timestamp'ler
- Context manager ile güvenli bağlantılar
- Kapsamlı CRUD işlemleri

Yazar: BiP Bot Development Team
Versiyon: 2.0.0
"""

import sqlite3
import logging
import os
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path='bip_bot.db'):
        """Veritabanı bağlantısını başlatır"""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Veritabanı tablolarını oluşturur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Events tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # Slots tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS slots (
                    slot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    start_datetime TIMESTAMP NOT NULL,
                    end_datetime TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_by TEXT,
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')
            
            # created_by kolonu zaten CREATE TABLE'da tanımlı
            
            # Slot votes tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS slot_votes (
                    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    slot_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    choice TEXT NOT NULL CHECK (choice IN ('yes', 'no')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (event_id),
                    FOREIGN KEY (slot_id) REFERENCES slots (slot_id),
                    UNIQUE(event_id, slot_id, user_id)
                )
            ''')
            
            # Polls tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS polls (
                    poll_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')
            
            # Poll choices tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poll_choices (
                    choice_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poll_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (poll_id) REFERENCES polls (poll_id)
                )
            ''')
            
            # Poll votes tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS poll_votes (
                    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    poll_id INTEGER NOT NULL,
                    choice_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (poll_id) REFERENCES polls (poll_id),
                    FOREIGN KEY (choice_id) REFERENCES poll_choices (choice_id),
                    UNIQUE(poll_id, user_id)
                )
            ''')
            
            # Expenses tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS expenses (
                    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    notes TEXT,
                    weight REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (event_id) REFERENCES events (event_id)
                )
            ''')
            
            # Users tablosu
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    role TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Veritabanı tabloları oluşturuldu/doğrulandı")
    
    @contextmanager
    def get_connection(self):
        """Veritabanı bağlantısı context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Dict-like access
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Veritabanı hatası: {str(e)}")
            raise
        finally:
            conn.close()
    
    # Events işlemleri
    def create_event(self, title, created_by, group_id):
        """Yeni etkinlik oluşturur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (title, created_by, group_id)
                VALUES (?, ?, ?)
            ''', (title, created_by, group_id))
            event_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Etkinlik oluşturuldu: {title} (ID: {event_id})")
            return event_id
    
    def get_latest_event(self, group_id=None):
        """En son etkinliği getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if group_id:
                cursor.execute('''
                    SELECT * FROM events 
                    WHERE group_id = ? AND status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                ''', (group_id,))
            else:
                cursor.execute('''
                    SELECT * FROM events 
                    WHERE status = 'active'
                    ORDER BY created_at DESC LIMIT 1
                ''')
            return cursor.fetchone()
    
    def get_event_by_id(self, event_id):
        """ID ile etkinlik getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM events WHERE event_id = ?', (event_id,))
            return cursor.fetchone()
    
    # Slots işlemleri
    def create_slot(self, event_id, start_datetime, end_datetime, created_by=None):
        """Yeni slot oluşturur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO slots (event_id, start_datetime, end_datetime, created_by)
                VALUES (?, ?, ?, ?)
            ''', (event_id, start_datetime, end_datetime, created_by))
            slot_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Slot oluşturuldu: {start_datetime} - {end_datetime} (ID: {slot_id})")
            return slot_id
    
    def get_slots_by_event(self, event_id):
        """Etkinliğe ait slotları getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM slots 
                WHERE event_id = ? AND status = 'active'
                ORDER BY start_datetime
            ''', (event_id,))
            return cursor.fetchall()
    
    def get_slot_by_id(self, slot_id):
        """ID'ye göre slot getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM slots WHERE slot_id = ?', (slot_id,))
            return cursor.fetchone()
    
    def vote_slot(self, event_id, slot_id, user_id, choice):
        """Slot için oy verir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO slot_votes 
                (event_id, slot_id, user_id, choice)
                VALUES (?, ?, ?, ?)
            ''', (event_id, slot_id, user_id, choice))
            conn.commit()
            logger.info(f"Slot oyu: Kullanıcı {user_id} -> Slot {slot_id} = {choice}")
    
    def get_slot_votes(self, event_id):
        """Etkinliğe ait slot oylarını getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT sv.*, s.start_datetime, s.end_datetime
                FROM slot_votes sv
                JOIN slots s ON sv.slot_id = s.slot_id
                WHERE sv.event_id = ?
            ''', (event_id,))
            return cursor.fetchall()
    
    # Polls işlemleri
    def create_poll(self, event_id, question):
        """Yeni anket oluşturur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO polls (event_id, question)
                VALUES (?, ?)
            ''', (event_id, question))
            poll_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Anket oluşturuldu: {question} (ID: {poll_id})")
            return poll_id
    
    def get_poll_by_event(self, event_id):
        """Etkinliğe ait anketi getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM polls 
                WHERE event_id = ? AND status = 'active'
                ORDER BY created_at DESC LIMIT 1
            ''', (event_id,))
            return cursor.fetchone()
    
    def create_poll_choice(self, poll_id, text, latitude=None, longitude=None):
        """Anket seçeneği oluşturur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO poll_choices (poll_id, text, latitude, longitude)
                VALUES (?, ?, ?, ?)
            ''', (poll_id, text, latitude, longitude))
            choice_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Anket seçeneği oluşturuldu: {text} (ID: {choice_id})")
            return choice_id
    
    def get_poll_choices(self, poll_id):
        """Anket seçeneklerini getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM poll_choices 
                WHERE poll_id = ?
                ORDER BY choice_id
            ''', (poll_id,))
            return cursor.fetchall()
    
    def vote_poll(self, poll_id, choice_id, user_id):
        """Anket için oy verir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO poll_votes 
                (poll_id, choice_id, user_id)
                VALUES (?, ?, ?)
            ''', (poll_id, choice_id, user_id))
            conn.commit()
            logger.info(f"Anket oyu: Kullanıcı {user_id} -> Seçenek {choice_id}")
    
    def get_poll_votes(self, poll_id):
        """Anket oylarını getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pv.*, pc.text
                FROM poll_votes pv
                JOIN poll_choices pc ON pv.choice_id = pc.choice_id
                WHERE pv.poll_id = ?
            ''', (poll_id,))
            return cursor.fetchall()
    
    # Expenses işlemleri
    def create_expense(self, event_id, user_id, amount, description, weight=1.0):
        """Yeni gider oluşturur"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO expenses (event_id, user_id, amount, notes, weight)
                VALUES (?, ?, ?, ?, ?)
            ''', (event_id, user_id, amount, description, weight))
            expense_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Gider oluşturuldu: {amount} TL - {description} (ID: {expense_id})")
            return expense_id
    
    def get_expenses_by_event(self, event_id):
        """Etkinliğe ait giderleri getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM expenses 
                WHERE event_id = ?
                ORDER BY created_at
            ''', (event_id,))
            return cursor.fetchall()
    
    # Users işlemleri
    def create_or_update_user(self, user_id, name=None, role='user'):
        """Kullanıcı oluşturur veya günceller"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, name, role, last_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, name, role))
            conn.commit()
            logger.info(f"Kullanıcı güncellendi: {user_id}")
    
    def get_user(self, user_id):
        """Kullanıcı bilgilerini getirir"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
    
    # Yardımcı fonksiyonlar
    def is_moderator(self, user_id, event_id):
        """Kullanıcının moderatör olup olmadığını kontrol eder"""
        event = self.get_event_by_id(event_id)
        if event:
            return event['created_by'] == user_id
        return False
    
    def get_event_summary(self, event_id):
        """Etkinlik özetini getirir"""
        event = self.get_event_by_id(event_id)
        if not event:
            return None
        
        slots = self.get_slots_by_event(event_id)
        slot_votes = self.get_slot_votes(event_id)
        
        poll = self.get_poll_by_event(event_id)
        poll_choices = []
        poll_votes = []
        if poll:
            poll_choices = self.get_poll_choices(poll['poll_id'])
            poll_votes = self.get_poll_votes(poll['poll_id'])
        
        expenses = self.get_expenses_by_event(event_id)
        
        return {
            'event': dict(event),
            'slots': [dict(slot) for slot in slots],
            'slot_votes': [dict(vote) for vote in slot_votes],
            'poll': dict(poll) if poll else None,
            'poll_choices': [dict(choice) for choice in poll_choices],
            'poll_votes': [dict(vote) for vote in poll_votes],
            'expenses': [dict(expense) for expense in expenses]
        }

# Global veritabanı instance
db = Database()

