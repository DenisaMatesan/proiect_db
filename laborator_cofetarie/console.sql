CREATE DATABASE IF NOT EXISTS laborator_cofetarie;
USE laborator_cofetarie;

CREATE TABLE UTILIZATORI (
    id_utilizator INT PRIMARY KEY AUTO_INCREMENT,
    nume VARCHAR(100) NOT NULL,
    parola VARCHAR(255) NOT NULL,
    rol ENUM('administrator', 'cofetar', 'vanzator') NOT NULL
);

CREATE TABLE FURNIZORI (
    id_furnizor INT PRIMARY KEY AUTO_INCREMENT,
    denumire VARCHAR(100) NOT NULL,
    telefon VARCHAR(15)
);

CREATE TABLE INGREDIENTE (
    id_ingredient INT PRIMARY KEY AUTO_INCREMENT,
    nume VARCHAR(100) NOT NULL,
    unitate_masura VARCHAR(10) NOT NULL,
    stoc_curent DECIMAL(10,3) DEFAULT 0,
    prag_minim DECIMAL(10,3) DEFAULT 0
);

CREATE TABLE CLIENTI (
    id_client INT PRIMARY KEY AUTO_INCREMENT,
    nume VARCHAR(100) NOT NULL,
    telefon VARCHAR(15) UNIQUE NOT NULL
);

CREATE TABLE LOTURI (
    id_lot INT PRIMARY KEY AUTO_INCREMENT,
    id_ingredient INT NOT NULL,
    id_furnizor INT NOT NULL,
    cantitate_ramasa DECIMAL(10,3) NOT NULL,
    data_receptiei DATETIME NOT NULL,
    data_expirarii DATE NOT NULL,
    FOREIGN KEY (id_ingredient) REFERENCES INGREDIENTE(id_ingredient),
    FOREIGN KEY (id_furnizor) REFERENCES FURNIZORI(id_furnizor)
);

CREATE TABLE RETETE (
    id_reteta INT PRIMARY KEY AUTO_INCREMENT,
    denumire VARCHAR(100) NOT NULL,
    portii_baza INT NOT NULL,
    sursa ENUM('manuala', 'generata_ai') NOT NULL,
    stare ENUM('ciorna', 'verificata', 'aprobata') NOT NULL,
    id_utilizator INT NOT NULL,
    FOREIGN KEY (id_utilizator) REFERENCES UTILIZATORI(id_utilizator)
);

CREATE TABLE RETETE_INGREDIENTE (
    id_reteta INT NOT NULL,
    id_ingredient INT NOT NULL,
    cantitate DECIMAL(10,3) NOT NULL,
    PRIMARY KEY (id_reteta, id_ingredient),
    FOREIGN KEY (id_reteta) REFERENCES RETETE(id_reteta),
    FOREIGN KEY (id_ingredient) REFERENCES INGREDIENTE(id_ingredient)
);

CREATE TABLE GENERARI_AI (
    id_generare INT PRIMARY KEY AUTO_INCREMENT,
    ingrediente_trimise TEXT NOT NULL,
    raspuns_ai TEXT NOT NULL,
    data_generarii DATETIME NOT NULL,
    id_utilizator INT NOT NULL,
    id_reteta INT,
    FOREIGN KEY (id_utilizator) REFERENCES UTILIZATORI(id_utilizator),
    FOREIGN KEY (id_reteta) REFERENCES RETETE(id_reteta)
);

CREATE TABLE PRODUSE (
    id_produs INT PRIMARY KEY AUTO_INCREMENT,
    denumire VARCHAR(100) NOT NULL,
    pret_vanzare DECIMAL(10,2) NOT NULL,
    activ BOOLEAN DEFAULT TRUE,
    id_reteta INT NOT NULL,
    FOREIGN KEY (id_reteta) REFERENCES RETETE(id_reteta)
);

CREATE TABLE COMENZI (
    id_comanda INT PRIMARY KEY AUTO_INCREMENT,
    data_livrare DATETIME NOT NULL,
    tip ENUM('rapida', 'custom') NOT NULL,
    stare ENUM('preluata', 'in_productie', 'finalizata') NOT NULL,
    text_personalizat VARCHAR(255),
    model_dorit VARCHAR(255),
    id_client INT NOT NULL,
    FOREIGN KEY (id_client) REFERENCES CLIENTI(id_client)
);

CREATE TABLE COMENZI_DETALII (
    id_detaliu INT PRIMARY KEY AUTO_INCREMENT,
    id_comanda INT NOT NULL,
    id_produs INT NOT NULL,
    cantitate INT NOT NULL,
    FOREIGN KEY (id_comanda) REFERENCES COMENZI(id_comanda),
    FOREIGN KEY (id_produs) REFERENCES PRODUSE(id_produs)
);

CREATE TABLE PRODUCTIE (
    id_sarcina INT PRIMARY KEY AUTO_INCREMENT,
    stare ENUM('in_asteptare', 'in_lucru', 'gata') NOT NULL,
    data_productie DATE NOT NULL,
    id_detaliu INT NOT NULL,
    id_comanda INT NOT NULL,
    id_utilizator INT NOT NULL,
    FOREIGN KEY (id_detaliu) REFERENCES COMENZI_DETALII(id_detaliu),
    FOREIGN KEY (id_comanda) REFERENCES COMENZI(id_comanda),
    FOREIGN KEY (id_utilizator) REFERENCES UTILIZATORI(id_utilizator)
);