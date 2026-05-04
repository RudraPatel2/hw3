-- Music DB schema for HW3
-- Note: MySQL string comparisons are case-insensitive by default with typical collations.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS rating;
DROP TABLE IF EXISTS song_genre;
DROP TABLE IF EXISTS song;
DROP TABLE IF EXISTS album;
DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS genre;
DROP TABLE IF EXISTS artist;

SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE artist (
  name            VARCHAR(150) NOT NULL,
  is_individual   BOOLEAN      NOT NULL,
  PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE genre (
  name            VARCHAR(50) NOT NULL,
  PRIMARY KEY (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE user (
  username        VARCHAR(50) NOT NULL,
  PRIMARY KEY (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE album (
  id              INT NOT NULL AUTO_INCREMENT,
  title           VARCHAR(150) NOT NULL,
  artist_name     VARCHAR(150) NOT NULL,
  genre_name      VARCHAR(50)  NOT NULL,
  release_date    DATE NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_album_title_artist (title, artist_name),
  CONSTRAINT fk_album_artist
    FOREIGN KEY (artist_name) REFERENCES artist(name)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_album_genre
    FOREIGN KEY (genre_name) REFERENCES genre(name)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE song (
  id              INT NOT NULL AUTO_INCREMENT,
  title           VARCHAR(150) NOT NULL,
  artist_name     VARCHAR(150) NOT NULL,
  album_id        INT NULL,
  release_date    DATE NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uniq_song_artist_title (artist_name, title),
  KEY idx_song_album (album_id),
  KEY idx_song_artist_release (artist_name, release_date),
  CONSTRAINT fk_song_artist
    FOREIGN KEY (artist_name) REFERENCES artist(name)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_song_album
    FOREIGN KEY (album_id) REFERENCES album(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE song_genre (
  song_id         INT NOT NULL,
  genre_name      VARCHAR(50) NOT NULL,
  PRIMARY KEY (song_id, genre_name),
  CONSTRAINT fk_song_genre_song
    FOREIGN KEY (song_id) REFERENCES song(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_song_genre_genre
    FOREIGN KEY (genre_name) REFERENCES genre(name)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rating (
  username        VARCHAR(50) NOT NULL,
  song_id         INT NOT NULL,
  score           TINYINT NOT NULL,
  rated_on        DATE NOT NULL,
  PRIMARY KEY (username, song_id),
  KEY idx_rating_date (rated_on),
  CONSTRAINT fk_rating_user
    FOREIGN KEY (username) REFERENCES user(username)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_rating_song
    FOREIGN KEY (song_id) REFERENCES song(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

