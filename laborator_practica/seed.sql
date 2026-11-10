USE laborator_cofetarie;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE PRODUCTIE;
TRUNCATE TABLE COMENZI_DETALII;
TRUNCATE TABLE COMENZI;
TRUNCATE TABLE PRODUSE;
TRUNCATE TABLE GENERARI_AI;
TRUNCATE TABLE RETETE_INGREDIENTE;
TRUNCATE TABLE RETETE;
TRUNCATE TABLE LOTURI;
TRUNCATE TABLE CLIENTI;
TRUNCATE TABLE INGREDIENTE;
TRUNCATE TABLE FURNIZORI;
TRUNCATE TABLE UTILIZATORI;
SET FOREIGN_KEY_CHECKS = 1;

-- 1. Utilizatori
INSERT INTO UTILIZATORI (nume, parola, rol) VALUES
('Elena Popescu', 'hash_parola_admin', 'administrator'),
('Mihai Ionescu', 'hash_parola_cofetar', 'cofetar'),
('Ana Radu', 'hash_parola_vanzator', 'vanzator');

-- 2. Furnizori
INSERT INTO FURNIZORI (denumire, telefon) VALUES
('Lactate LactoSud SRL', '0722111222'),
('Ingrediente Premium SRL', '0733333444');

-- 3. Ingrediente (Stocuri sub pragul minim pentru testare)
INSERT INTO INGREDIENTE (nume, unitate_masura, stoc_curent, prag_minim) VALUES
('Făină 000', 'kg', 50.000, 10.000),
('Zahăr Tos', 'kg', 3.000, 5.000), -- Sub prag
('Unt 82%', 'kg', 2.000, 3.000),   -- Sub prag
('Ciocolată Neagră 70%', 'kg', 8.000, 2.000);

-- 4. Clienți
INSERT INTO CLIENTI (nume, telefon) VALUES
('Maria Georgescu', '0744555666'),
('Cristian Vasilescu', '0755888999');

-- 5. Loturi (FEFO)
INSERT INTO LOTURI (id_ingredient, id_furnizor, cantitate_ramasa, data_receptiei, data_expirarii) VALUES
(3, 1, 5.000, '2026-11-01 08:00:00', DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
(3, 1, 7.500, '2026-11-05 09:30:00', DATE_ADD(CURDATE(), INTERVAL 15 DAY)),
(4, 2, 8.000, '2026-11-02 10:00:00', DATE_ADD(CURDATE(), INTERVAL 30 DAY));

-- 6. Rețete (Inclusiv ciornă și verificată pentru modulul AI)
INSERT INTO RETETE (denumire, portii_baza, sursa, stare, id_utilizator) VALUES
('Tort Amandină', 10, 'manuala', 'aprobata', 1),
('Ecler cu Ciocolată', 12, 'generata_ai', 'verificata', 2),
('Tarta de Lămâie', 8, 'generata_ai', 'ciorna', 2);

-- 7. Rețete - Ingrediente
INSERT INTO RETETE_INGREDIENTE (id_reteta, id_ingredient, cantitate) VALUES
(1, 1, 0.500),
(1, 2, 0.400),
(1, 3, 0.300),
(1, 4, 0.200),
(2, 4, 0.400);

-- 8. Generări AI
INSERT INTO GENERARI_AI (ingrediente_trimise, raspuns_ai, data_generarii, id_utilizator, id_reteta) VALUES
('ouă, lapte, ciocolată neagră', 'Rețetă Ecler obținută cu succes.', NOW(), 2, 2),
('lămâie, unt, zahăr', 'Rețetă Tartă Lămâie generată.', NOW(), 2, 3);

-- 9. Produse
INSERT INTO PRODUSE (denumire, pret_vanzare, activ, id_reteta) VALUES
('Tort Amandină Intreg', 150.00, 1, 1),
('Ecler Ciocolată Bucată', 12.50, 1, 2);

-- 10. Comenzi (Inclusiv comenzi finalizate pentru vânzări)
INSERT INTO COMENZI (data_livrare, tip, stare, text_personalizat, model_dorit, id_client) VALUES
(NOW(), 'custom', 'in_productie', 'La Mulți Ani Maria!', 'Model Aniversar Flori', 1),
(NOW(), 'rapida', 'finalizata', NULL, NULL, 1),
(NOW(), 'rapida', 'finalizata', NULL, NULL, 2);

-- 11. Comenzi Detalii (Cantități mari pentru a depăși pragul de 200 lei la HAVING)
INSERT INTO COMENZI_DETALII (id_comanda, id_produs, cantitate) VALUES
(1, 1, 1),
(2, 1, 2), -- 300 lei
(3, 2, 10);

-- 12. Producție (Alocată pentru ziua curentă - CURDATE)
INSERT INTO PRODUCTIE (stare, data_productie, id_detaliu, id_comanda, id_utilizator) VALUES
('in_lucru', CURDATE(), 1, 1, 2);