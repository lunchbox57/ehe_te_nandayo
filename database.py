from contextlib import closing
import sqlite3 as sql
import util as ut

DB = 'paimon.db'


def setup_db():
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    uid INTEGER PRIMARY KEY,
                    resin INTEGER DEFAULT 0,
                    warn INTEGER DEFAULT 150,
                    notifications INTEGER DEFAULT 1,
                    timezone TEXT DEFAULT 'null:null',
                    strikes INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS banned (
                    uid INTEGER PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS codes (
                    rewards TEXT,
                    expired INTEGER DEFAULT 0,
                    notified INTEGER DEFAULT 0,
                    eu_code TEXT PRIMARY KEY,
                    na_code TEXT,
                    sea_code TEXT
                );
                """
            )


def get_strikes(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT strikes FROM users '
                        'WHERE uid = ?',
                        [uid])
            return cur.fetchone()[0]  # (x,)


def inc_strikes(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET strikes = strikes + 1 '
                        'WHERE uid = ?',
                        [uid])
            db.commit()


def dec_strikes(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET strikes = strikes - 1 '
                        'WHERE strikes > 0 AND uid = ?',
                        [uid])
            db.commit()


def banned(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                'SELECT EXISTS ('
                'SELECT 1 FROM banned WHERE uid = ?'
                ')',
                [uid])
            return cur.fetchone()[0]


def ban_user(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('INSERT INTO banned VALUES (?)',
                        [uid])
            db.commit()
            ut.blocked(uid)


def cached(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                'SELECT EXISTS ('
                'SELECT 1 FROM users WHERE uid = ?'
                ')',
                [uid])
            return cur.fetchone()[0]


def add_user(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('INSERT INTO users (uid) VALUES (?)',
                        [uid])
            db.commit()


def del_user(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('DELETE FROM users '
                        'WHERE uid = ?',
                        [uid])
            db.commit()


def all_users():
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT uid FROM users')
            return cur.fetchall()


def all_users_notify():
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT uid FROM users WHERE notifications = 1')
            return cur.fetchall()


def get_resin(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT resin FROM users '
                        'WHERE uid = ?',
                        [uid])
            return cur.fetchone()[0]


def set_resin(uid, resin):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET resin = ? '
                        'WHERE uid = ?',
                        [resin, uid])
            db.commit()


def inc_resin(uid, resin):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                f'UPDATE users SET resin = resin + ? '
                f'WHERE resin < {ut.RESIN_MAX} '
                f'AND uid = ?',
                [resin, uid])
            db.commit()


def dec_resin(uid, resin):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                'UPDATE users SET resin = resin - ? '
                'WHERE resin > 0 '
                'AND uid = ?',
                [resin, uid])
            db.commit()


def max_resin(uid, resin):
    cur_resin = get_resin(uid)
    hard_cap = (ut.RESIN_MAX - cur_resin) * ut.RESIN_REGEN
    soft_cap = (resin - cur_resin) * ut.RESIN_REGEN
    soft_cap = 0 if soft_cap < 0 else soft_cap
    return (hard_cap // 60, hard_cap % 60), (soft_cap // 60, soft_cap % 60)


def unset_warn(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET warn = -1 '
                        'WHERE uid = ?',
                        [uid])
            db.commit()


def get_warn(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT warn FROM users '
                        'WHERE uid = ?',
                        [uid])
            return cur.fetchone()[0]  # (x,)


def set_warn(uid, threshold):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET warn = ? '
                        'WHERE uid = ?',
                        [threshold, uid])
            db.commit()


def unset_timezone(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET timezone = "null:null" '
                        'WHERE uid = ?',
                        [uid])
            db.commit()


def get_timezone(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT timezone FROM users '
                        'WHERE uid = ?',
                        [uid])
            return cur.fetchone()[0]  # (x,)


def set_timezone(uid, hour, minutes):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET timezone = ? '
                        'WHERE uid = ?',
                        [f"{hour:02}:{minutes:02}", uid])
            db.commit()


def code_cached(code):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT EXISTS ('
                        'SELECT 1 FROM codes WHERE eu_code = ?'
                        ')',
                        [code])
            return cur.fetchone()[0]


def _expired(expired):
    return int(expired.lower() == 'yes')


def add_code(rewards, expired, eu_code, na_code, sea_code):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            notified = expired = _expired(expired)
            if code_cached(eu_code):
                cur.execute('UPDATE codes SET expired = ? '
                            'WHERE eu_code = ?',
                            [expired, eu_code])
            else:
                cur.execute(
                    'INSERT INTO codes '
                    '(rewards, expired, notified, eu_code, na_code, sea_code) '
                    'VALUES (?, ?, ?, ?, ?, ?)',
                    [rewards, expired, notified, eu_code, na_code, sea_code])

            db.commit()


def info_code(eu_code, info):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute(f'SELECT {info} FROM codes '
                        f'WHERE eu_code = ?',
                        [eu_code])
            return cur.fetchone()[0]  # (x,)


def mark_codes(codes):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.executemany('UPDATE codes SET notified = 1 '
                            'WHERE eu_code = ?',
                            codes)
            db.commit()


def unmarked_codes():
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT rewards, eu_code, na_code, sea_code '
                        'FROM codes '
                        'WHERE notified = 0 AND expired = 0')
            return cur.fetchall()


def unexpired_codes():
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT rewards, eu_code, na_code, sea_code '
                        'FROM codes '
                        'WHERE expired = 0')
            return cur.fetchall()


def unset_notifications(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET notifications = -1 '
                        'WHERE uid = ?',
                        [uid])
            db.commit()


def get_notifications(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('SELECT notifications FROM users '
                        'WHERE uid = ?',
                        [uid])
            return cur.fetchone()[0]  # (x,)


def set_notifications(uid):
    with closing(sql.connect(DB)) as db:
        with closing(db.cursor()) as cur:
            cur.execute('UPDATE users SET notifications = 1 '
                        'WHERE uid = ?',
                        [uid])
            db.commit()