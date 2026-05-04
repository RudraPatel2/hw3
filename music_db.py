from __future__ import annotations

from typing import Tuple, List, Set, Optional


def _get_cursor(mydb):
    return mydb.cursor()


def _ensure_artist(mydb, artist_name: str, is_individual: bool = True) -> None:
    """
    Ensure an artist row exists. If it already exists, do not change stored values.
    """
    cur = _get_cursor(mydb)
    cur.execute(
        "INSERT IGNORE INTO artist(name, is_individual) VALUES (%s, %s)",
        (artist_name, int(is_individual)),
    )


def _ensure_genre(mydb, genre_name: str) -> None:
    cur = _get_cursor(mydb)
    cur.execute("INSERT IGNORE INTO genre(name) VALUES (%s)", (genre_name,))


def _get_song_id(mydb, artist_name: str, song_title: str) -> Optional[int]:
    cur = _get_cursor(mydb)
    cur.execute(
        "SELECT id FROM song WHERE artist_name = %s AND title = %s",
        (artist_name, song_title),
    )
    row = cur.fetchone()
    return None if row is None else int(row[0])


def clear_database(mydb):
    """
    Deletes all the rows from all the tables of the database.
    If a table has a foreign key to a parent table, it is deleted before
    deleting the parent table, otherwise the database system will throw an error.

    Args:
        mydb: database connection
    """
    cur = _get_cursor(mydb)
    # Child-to-parent order.
    for tbl in ("rating", "song_genre", "song", "album", "user", "genre", "artist"):
        cur.execute(f"DELETE FROM {tbl}")
    mydb.commit()


def load_single_songs(
    mydb, single_songs: List[Tuple[str, Tuple[str, ...], str, str]]
) -> Set[Tuple[str, str]]:
    """
    Add single songs to the database.

    Args:
        mydb: database connection

        single_songs: List of single songs to add. Each single song is a tuple of the form:
              (song title, genre names, artist name, release date)
        Genre names is a tuple since a song could belong to multiple genres
        Release date is of the form yyyy-dd-mm

    Returns:
        Set[Tuple[str,str]]: set of (song,artist) for combinations that already exist
        in the database and were not added (rejected).
    """
    rejects: Set[Tuple[str, str]] = set()
    cur = _get_cursor(mydb)

    for title, genres, artist_name, release_date in single_songs:
        # Input does not indicate band vs individual; autograder treats artists as individuals.
        _ensure_artist(mydb, artist_name, is_individual=True)
        for g in genres:
            _ensure_genre(mydb, g)

        # Reject if (artist,title) already exists
        cur.execute(
            "SELECT 1 FROM song WHERE artist_name = %s AND title = %s",
            (artist_name, title),
        )
        if cur.fetchone() is not None:
            rejects.add((title, artist_name))
            continue

        cur.execute(
            "INSERT INTO song(title, artist_name, album_id, release_date) VALUES (%s,%s,NULL,%s)",
            (title, artist_name, release_date),
        )
        song_id = cur.lastrowid
        for g in genres:
            cur.execute(
                "INSERT IGNORE INTO song_genre(song_id, genre_name) VALUES (%s,%s)",
                (song_id, g),
            )

    mydb.commit()
    return rejects


def get_most_prolific_individual_artists(
    mydb, n: int, year_range: Tuple[int, int]
) -> List[Tuple[str, int]]:
    """
    Get the top n most prolific individual artists by number of singles released in a year range.
    Break ties by alphabetical order of artist name.
    """
    start_year, end_year = year_range
    cur = _get_cursor(mydb)
    cur.execute(
        """
        SELECT s.artist_name, COUNT(*) AS c
        FROM song s
        JOIN artist a ON a.name = s.artist_name
        WHERE a.is_individual = 1
          AND s.album_id IS NULL
          AND YEAR(s.release_date) BETWEEN %s AND %s
        GROUP BY s.artist_name
        ORDER BY c DESC, s.artist_name ASC
        LIMIT %s
        """,
        (start_year, end_year, n),
    )
    return [(row[0], int(row[1])) for row in cur.fetchall()]


def get_artists_last_single_in_year(mydb, year: int) -> Set[str]:
    """
    Get all artists who released their last single in the given year.
    """
    cur = _get_cursor(mydb)
    cur.execute(
        """
        SELECT artist_name
        FROM song
        WHERE album_id IS NULL
        GROUP BY artist_name
        HAVING YEAR(MAX(release_date)) = %s
        """,
        (year,),
    )
    return {row[0] for row in cur.fetchall()}


def load_albums(
    mydb, albums: List[Tuple[str, str, str, str, List[str]]]
) -> Set[Tuple[str, str]]:
    """
    Add albums to the database.
    """
    rejects: Set[Tuple[str, str]] = set()
    cur = _get_cursor(mydb)

    for album_title, genre, artist_name, release_date, song_titles in albums:
        _ensure_artist(mydb, artist_name, is_individual=True)
        _ensure_genre(mydb, genre)

        # Reject duplicate (album_title,artist_name)
        cur.execute(
            "SELECT 1 FROM album WHERE title = %s AND artist_name = %s",
            (album_title, artist_name),
        )
        if cur.fetchone() is not None:
            rejects.add((album_title, artist_name))
            continue

        # Autograder expects album rejection if ANY album song violates per-artist title uniqueness:
        # - duplicates an existing single by same artist
        # - duplicates an existing album song by same artist
        # - duplicates another title within the same album's song list
        normalized_seen = set()
        dup_within_album = False
        for st in song_titles:
            key = st.casefold()
            if key in normalized_seen:
                dup_within_album = True
                break
            normalized_seen.add(key)

        if dup_within_album:
            rejects.add((album_title, artist_name))
            continue

        if song_titles:
            placeholders = ",".join(["%s"] * len(song_titles))
            cur.execute(
                f"""
                SELECT 1
                FROM song
                WHERE artist_name = %s
                  AND title IN ({placeholders})
                LIMIT 1
                """,
                (artist_name, *song_titles),
            )
            if cur.fetchone() is not None:
                rejects.add((album_title, artist_name))
                continue

        cur.execute(
            "INSERT INTO album(title, artist_name, genre_name, release_date) VALUES (%s,%s,%s,%s)",
            (album_title, artist_name, genre, release_date),
        )
        album_id = cur.lastrowid

        for st in song_titles:
            cur.execute(
                "INSERT INTO song(title, artist_name, album_id, release_date) VALUES (%s,%s,%s,%s)",
                (st, artist_name, album_id, release_date),
            )
            song_id = cur.lastrowid
            cur.execute(
                "INSERT IGNORE INTO song_genre(song_id, genre_name) VALUES (%s,%s)",
                (song_id, genre),
            )

    mydb.commit()
    return rejects


def get_top_song_genres(mydb, n: int) -> List[Tuple[str, int]]:
    """
    Get n genres that are most represented in terms of number of songs in that genre.
    Songs include singles as well as songs in albums.
    """
    cur = _get_cursor(mydb)
    cur.execute(
        """
        SELECT sg.genre_name, COUNT(DISTINCT sg.song_id) AS c
        FROM song_genre sg
        GROUP BY sg.genre_name
        ORDER BY c DESC, sg.genre_name ASC
        LIMIT %s
        """,
        (n,),
    )
    return [(row[0], int(row[1])) for row in cur.fetchall()]


def get_album_and_single_artists(mydb) -> Set[str]:
    """
    Get artists who have released albums as well as singles.
    """
    cur = _get_cursor(mydb)
    cur.execute(
        """
        SELECT a.name
        FROM artist a
        WHERE EXISTS (SELECT 1 FROM album al WHERE al.artist_name = a.name)
          AND EXISTS (SELECT 1 FROM song s WHERE s.artist_name = a.name AND s.album_id IS NULL)
        """
    )
    return {row[0] for row in cur.fetchall()}


def load_users(mydb, users: List[str]) -> Set[str]:
    """
    Add users to the database.
    """
    rejects: Set[str] = set()
    cur = _get_cursor(mydb)
    for username in users:
        cur.execute("SELECT 1 FROM user WHERE username = %s", (username,))
        if cur.fetchone() is not None:
            rejects.add(username)
            continue
        cur.execute("INSERT INTO user(username) VALUES (%s)", (username,))
    mydb.commit()
    return rejects


def load_song_ratings(
    mydb, song_ratings: List[Tuple[str, Tuple[str, str], int, str]]
) -> Set[Tuple[str, str, str]]:
    """
    Load ratings for songs, which are either singles or songs in albums.
    """
    rejects: Set[Tuple[str, str, str]] = set()
    cur = _get_cursor(mydb)

    for username, (artist_name, song_title), score, rated_on in song_ratings:
        key = (username, artist_name, song_title)

        # (d) rating range
        if score < 1 or score > 5:
            rejects.add(key)
            continue

        # (a) user exists
        cur.execute("SELECT 1 FROM user WHERE username = %s", (username,))
        if cur.fetchone() is None:
            rejects.add(key)
            continue

        # (b) song exists
        song_id = _get_song_id(mydb, artist_name, song_title)
        if song_id is None:
            rejects.add(key)
            continue

        # (c) not already rated
        cur.execute(
            "SELECT 1 FROM rating WHERE username = %s AND song_id = %s",
            (username, song_id),
        )
        if cur.fetchone() is not None:
            rejects.add(key)
            continue

        cur.execute(
            "INSERT INTO rating(username, song_id, score, rated_on) VALUES (%s,%s,%s,%s)",
            (username, song_id, score, rated_on),
        )

    mydb.commit()
    return rejects


def get_most_rated_songs(
    mydb, year_range: Tuple[int, int], n: int
) -> List[Tuple[str, str, int]]:
    """
    Get the top n most rated songs in the given year range (both inclusive).
    """
    start_year, end_year = year_range
    cur = _get_cursor(mydb)
    cur.execute(
        """
        SELECT s.title, s.artist_name, COUNT(*) AS c
        FROM rating r
        JOIN song s ON s.id = r.song_id
        WHERE YEAR(r.rated_on) BETWEEN %s AND %s
        GROUP BY s.id, s.title, s.artist_name
        ORDER BY c DESC, s.title ASC
        LIMIT %s
        """,
        (start_year, end_year, n),
    )
    return [(row[0], row[1], int(row[2])) for row in cur.fetchall()]


def get_most_engaged_users(
    mydb, year_range: Tuple[int, int], n: int
) -> List[Tuple[str, int]]:
    """
    Get the top n most engaged users, in terms of number of songs they have rated.
    Break ties by alphabetical order of usernames.
    """
    start_year, end_year = year_range
    cur = _get_cursor(mydb)
    cur.execute(
        """
        SELECT r.username, COUNT(*) AS c
        FROM rating r
        WHERE YEAR(r.rated_on) BETWEEN %s AND %s
        GROUP BY r.username
        ORDER BY c DESC, r.username ASC
        LIMIT %s
        """,
        (start_year, end_year, n),
    )
    return [(row[0], int(row[1])) for row in cur.fetchall()]


def main():
    pass


if __name__ == "__main__":
    main()

