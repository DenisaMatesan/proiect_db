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

-- 1. Utilizatori (format nume.rol cu parole hash)
INSERT INTO UTILIZATORI (nume, parola, rol) VALUES
('elena.admin', '931951d5d9ebd16078e600e6bca319f174370dfdf9d781165dd12c033a9b000f', 'administrator'), -- admin123
('mihai.cofetar', '1412f5a68d1a85ce6742cdb2ebbda954221fc92427ff698b97cf06543efd2b19', 'cofetar'),       -- cofetar123
('ana.vanzator', '4fb0506490f79cff677c304c120413277ecf0356df74d44699bd6dbd43756829', 'vanzator');        -- vanzator123

-- 2. Furnizori
INSERT INTO FURNIZORI (denumire, telefon) VALUES
('Lactate LactoSud SRL', '0722111222'),
('Ingrediente Premium SRL', '0733333444'),
('Fructe Exotice Import SRL', '0744999888'),
('Delicii & Arome Italice SRL', '0755123789'),
('Depozitul de Cacao & Ciocolată', '0766444555');

-- 3. Ingrediente (cu praguri minime realiste pentru patiserie artizanala)
INSERT INTO INGREDIENTE (nume, unitate_masura, stoc_curent, prag_minim) VALUES
('Făină 000', 'kg', 0.000, 15.000),
('Zahăr Tos', 'kg', 0.000, 8.000),
('Unt 82%', 'kg', 0.000, 5.000),
('Ciocolată Neagră 70%', 'kg', 0.000, 3.000),
('Ciocolată Albă Callebaut', 'kg', 0.000, 2.500),
('Fructul Pasiunii / Mango', 'kg', 0.000, 3.000),
('Zmeură Proaspătă', 'kg', 0.000, 2.000),
('Fistic Granulat de Bronte', 'kg', 0.000, 1.500),
('Mascarpone Cremoso', 'kg', 0.000, 4.000),
('Smântână Dulce 35%', 'l', 0.000, 6.000),
('Vanilie Bourbon de Madagascar', 'kg', 0.000, 0.500),
('Ouă Proaspete', 'buc', 0.000, 60.000),
('Cafea Espresso Arabica', 'kg', 0.000, 1.000),
('Lapte Integral 3.5%', 'l', 0.000, 10.000),
('Lămâi Bio de Sicilia', 'kg', 0.000, 3.000);

-- 4. Clienți
INSERT INTO CLIENTI (nume, telefon) VALUES
('Maria Georgescu', '0744555666'),
('Cristian Vasilescu', '0755888999'),
('Ioana Dumitrescu', '0766123456'),
('Alexandru Popa', '0722998877'),
('Andreea Marin', '0733112233'),
('Mihai Stănescu', '0745001122'),
('Camelia Enache', '0788334455');

-- 5. Loturi (cu date FEFO variate: unele ce expira in 2-4 zile pentru a declansa alerte si modulul AI anti-risipa)
INSERT INTO LOTURI (id_ingredient, id_furnizor, cantitate_ramasa, data_receptiei, data_expirarii) VALUES
-- Faina (lot generos, termen lung)
(1, 2, 45.000, '2026-11-01 08:00:00', DATE_ADD(CURDATE(), INTERVAL 60 DAY)),
-- Zahar (sub pragul de 8kg)
(2, 2, 4.500, '2026-11-01 08:00:00', DATE_ADD(CURDATE(), INTERVAL 90 DAY)),
-- Unt (lot 1 expira in 3 zile - URGENT, lot 2 in 18 zile)
(3, 1, 2.000, '2026-11-02 09:00:00', DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
(3, 1, 4.000, '2026-11-10 10:30:00', DATE_ADD(CURDATE(), INTERVAL 18 DAY)),
-- Ciocolata Neagra 70%
(4, 5, 8.500, '2026-11-05 11:00:00', DATE_ADD(CURDATE(), INTERVAL 45 DAY)),
-- Ciocolata Alba
(5, 5, 3.200, '2026-11-08 14:00:00', DATE_ADD(CURDATE(), INTERVAL 40 DAY)),
-- Fructul Pasiunii / Mango (expira in 4 zile - excelent pentru AI!)
(6, 3, 2.800, '2026-11-12 08:30:00', DATE_ADD(CURDATE(), INTERVAL 4 DAY)),
-- Zmeura Proaspata (expira in 2 zile - URGENT!)
(7, 3, 1.800, '2026-11-15 09:15:00', DATE_ADD(CURDATE(), INTERVAL 2 DAY)),
-- Fistic Granulat
(8, 4, 2.500, '2026-11-03 10:00:00', DATE_ADD(CURDATE(), INTERVAL 90 DAY)),
-- Mascarpone (sub prag 4kg)
(9, 1, 2.500, '2026-11-14 08:00:00', DATE_ADD(CURDATE(), INTERVAL 8 DAY)),
-- Smantana Dulce 35% (expira in 3 zile - URGENT!)
(10, 1, 4.000, '2026-11-15 08:00:00', DATE_ADD(CURDATE(), INTERVAL 3 DAY)),
-- Vanilie Bourbon
(11, 4, 0.400, '2026-10-20 11:00:00', DATE_ADD(CURDATE(), INTERVAL 120 DAY)),
-- Oua (sub prag 60 buc)
(12, 1, 45.000, '2026-11-16 07:30:00', DATE_ADD(CURDATE(), INTERVAL 10 DAY)),
-- Cafea Espresso
(13, 4, 3.000, '2026-11-01 12:00:00', DATE_ADD(CURDATE(), INTERVAL 180 DAY)),
-- Lapte Integral
(14, 1, 15.000, '2026-11-14 08:00:00', DATE_ADD(CURDATE(), INTERVAL 7 DAY)),
-- Lamai Bio
(15, 3, 4.000, '2026-11-10 09:00:00', DATE_ADD(CURDATE(), INTERVAL 14 DAY));

-- 6. Rețete (Manuale și Generate AI în diferite stadii)
INSERT INTO RETETE (denumire, portii_baza, sursa, stare, id_utilizator) VALUES
('Tort Amandină Tradițională', 10, 'manuala', 'aprobata', 1),
('Ecler cu Ciocolată și Ganache', 12, 'generata_ai', 'aprobata', 2),
('Pavlova cu Fructe de Pădure & Fistic', 8, 'manuala', 'aprobata', 2),
('Tiramisu Artizanal cu Mascarpone', 10, 'manuala', 'aprobata', 1),
('Tartă cu Lămâie de Sicilia și Bezea', 8, 'manuala', 'aprobata', 2),
('Tort Red Velvet Velvet Delice', 12, 'generata_ai', 'verificata', 2),
('Mousse Exotique cu Mango & Fructul Pasiunii', 10, 'generata_ai', 'ciorna', 2);

-- 7. Rețete - Ingrediente (cantități per rețetă de bază)
INSERT INTO RETETE_INGREDIENTE (id_reteta, id_ingredient, cantitate) VALUES
-- 1. Tort Amandina (10 portii)
(1, 1, 0.500), -- Faina
(1, 2, 0.400), -- Zahar
(1, 3, 0.350), -- Unt
(1, 4, 0.250), -- Ciocolata neagra
(1, 12, 4.000), -- Oua
-- 2. Ecler cu Ciocolata (12 portii)
(2, 1, 0.250), -- Faina
(2, 3, 0.150), -- Unt
(2, 4, 0.300), -- Ciocolata neagra
(2, 10, 0.250), -- Smantana
(2, 12, 4.000), -- Oua
-- 3. Pavlova cu Fructe & Fistic (8 portii)
(3, 2, 0.300), -- Zahar
(3, 7, 0.350), -- Zmeura
(3, 8, 0.100), -- Fistic
(3, 10, 0.300), -- Smantana
(3, 12, 4.000), -- Albusuri
-- 4. Tiramisu (10 portii)
(4, 9, 0.500), -- Mascarpone
(4, 2, 0.150), -- Zahar
(4, 10, 0.250), -- Smantana
(4, 13, 0.050), -- Cafea
(4, 12, 3.000), -- Oua
-- 5. Tarta Lamai (8 portii)
(5, 1, 0.250), -- Faina
(5, 2, 0.250), -- Zahar
(5, 3, 0.200), -- Unt
(5, 15, 0.300), -- Lamai
(5, 12, 3.000), -- Oua
-- 6. Red Velvet (12 portii)
(6, 1, 0.400),
(6, 2, 0.350),
(6, 3, 0.250),
(6, 9, 0.300),
(6, 12, 3.000),
-- 7. Mousse Exotique (10 portii)
(7, 6, 0.450), -- Mango
(7, 5, 0.250), -- Ciocolata alba
(7, 10, 0.350); -- Smantana

-- 8. Generări AI
INSERT INTO GENERARI_AI (ingrediente_trimise, raspuns_ai, data_generarii, id_utilizator, id_reteta) VALUES
('ciocolată neagră, smântână, ouă', 'Rețetă Ecler cu Ganache catifelat de ciocolată generată cu succes.', DATE_SUB(NOW(), INTERVAL 5 DAY), 2, 2),
('unt, mascarpone, cacao, făină', 'Rețetă Tort Red Velvet cu cremă fină de brânză și vanilie bourbon.', DATE_SUB(NOW(), INTERVAL 2 DAY), 2, 6),
('mango, fructul pasiunii, ciocolată albă', 'Rețetă Mousse Exotique cu jeleu proaspăt de fructe exotice și oglindă albă.', NOW(), 2, 7);

-- 9. Produse (doar din rețetele aprobate)
INSERT INTO PRODUSE (denumire, pret_vanzare, activ, id_reteta) VALUES
('Tort Amandină Tradițional (1.2 kg)', 155.00, 1, 1),
('Ecler Ciocolată & Ganache Bucată', 16.50, 1, 2),
('Pavlova Festivă cu Zmeură & Fistic', 28.00, 1, 3),
('Tiramisu Delice la Pahar', 24.00, 1, 4),
('Tartă cu Lămâie & Bezea Caramelizată', 22.00, 1, 5);

-- 10. Comenzi (Diverse: finalizate luna curentă, în producție, personalizate)
INSERT INTO COMENZI (data_livrare, tip, stare, text_personalizat, model_dorit, id_client) VALUES
-- Comanda 1: Maria Georgescu (Custom, in productie)
(NOW(), 'custom', 'in_productie', 'La Mulți Ani Maria!', 'Model Aniversar Flori Pastel Roz', 1),
-- Comanda 2: Cristian Vasilescu (Comanda mare, finalizata -> depaseste 200 lei la HAVING)
(DATE_SUB(NOW(), INTERVAL 2 DAY), 'rapida', 'finalizata', NULL, NULL, 2),
-- Comanda 3: Ioana Dumitrescu (Comanda rapida finalizata)
(DATE_SUB(NOW(), INTERVAL 1 DAY), 'rapida', 'finalizata', NULL, NULL, 3),
-- Comanda 4: Alexandru Popa (Custom festiva, finalizata -> depaseste 200 lei)
(DATE_SUB(NOW(), INTERVAL 3 DAY), 'custom', 'finalizata', 'Botez Sofia - Bun Venit!', 'Norișori pufoși și fundițe roz', 4),
-- Comanda 5: Andreea Marin (Preluata, recenta)
(DATE_ADD(NOW(), INTERVAL 1 DAY), 'rapida', 'preluata', NULL, NULL, 5),
-- Comanda 6: Camelia Enache (Custom, in lucru)
(DATE_ADD(NOW(), INTERVAL 2 DAY), 'custom', 'in_productie', 'Nuntă Fericită Ioana & Radu', 'Trei etaje, perle de zahăr și bezea', 7);

-- 11. Comenzi Detalii (cantități care generează încasări reale)
INSERT INTO COMENZI_DETALII (id_comanda, id_produs, cantitate) VALUES
(1, 1, 1),   -- Comanda 1: 1 Tort Amandina (155 lei)
(1, 2, 4),   --            4 Eclere (66 lei) -> Total: 221 lei
(2, 1, 2),   -- Comanda 2: 2 Torturi Amandina (310 lei) -> depaseste 200 lei
(3, 2, 6),   -- Comanda 3: 6 Eclere (99 lei)
(3, 4, 2),   --            2 Tiramisu (48 lei) -> Total: 147 lei
(4, 1, 1),   -- Comanda 4: 1 Tort Amandina (155 lei)
(4, 3, 4),   --            4 Pavlova (112 lei) -> Total: 267 lei (depaseste 200 lei)
(5, 5, 2),   -- Comanda 5: 2 Tarte Lamai (44 lei)
(6, 1, 2),   -- Comanda 6: 2 Torturi Amandina (310 lei)
(6, 3, 6);   --            6 Pavlova (168 lei) -> Total: 478 lei

-- 12. Producție (sarcini alocate pe ziua de azi și următoarele)
INSERT INTO PRODUCTIE (stare, data_productie, id_detaliu, id_comanda, id_utilizator) VALUES
('in_lucru', CURDATE(), 1, 1, 2),
('in_asteptare', CURDATE(), 2, 1, 2),
('in_asteptare', DATE_ADD(CURDATE(), INTERVAL 1 DAY), 7, 5, 2),
('in_lucru', DATE_ADD(CURDATE(), INTERVAL 2 DAY), 8, 6, 2),
('in_asteptare', DATE_ADD(CURDATE(), INTERVAL 2 DAY), 9, 6, 2);
