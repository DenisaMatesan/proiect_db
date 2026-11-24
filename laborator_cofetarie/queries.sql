USE laborator_cofetarie;

-- 1. Gestiunea stocurilor

-- 1.1. Stocuri Critice (Ingrediente sub pragul minim)
SELECT id_ingredient, nume, stoc_curent, prag_minim, unitate_masura
FROM INGREDIENTE
WHERE stoc_curent <= prag_minim;

-- 1.2. Algoritmul FEFO – Loturi active ordonate după data expirării
SELECT l.id_lot, i.nume AS ingredient, l.cantitate_ramasa, l.data_expirarii, f.denumire AS furnizor
FROM LOTURI l
JOIN INGREDIENTE i ON l.id_ingredient = i.id_ingredient
JOIN FURNIZORI f ON l.id_furnizor = f.id_furnizor
WHERE l.cantitate_ramasa > 0 AND l.data_expirarii >= CURDATE()
ORDER BY l.data_expirarii ASC;

-- 1.3. Loturi urgente (care expiră în următoarele 7 zile)
SELECT l.id_lot, i.nume AS ingredient, l.cantitate_ramasa, l.data_expirarii
FROM LOTURI l
JOIN INGREDIENTE i ON l.id_ingredient = i.id_ingredient
WHERE l.data_expirarii <= DATE_ADD(CURDATE(), INTERVAL 7 DAY) AND l.cantitate_ramasa > 0;

-- 1.4. Total ingrediente recepționate per Furnizor
SELECT f.denumire AS furnizor, COUNT(l.id_lot) AS total_loturi, SUM(l.cantitate_ramasa) AS cantitate_totala
FROM FURNIZORI f
LEFT JOIN LOTURI l ON f.id_furnizor = l.id_furnizor
GROUP BY f.id_furnizor, f.denumire;

-- 1.5. Istoric recepții materii prime într-o perioadă dată
SELECT l.id_lot, i.nume AS ingredient, l.cantitate_ramasa, l.data_receptiei
FROM LOTURI l
JOIN INGREDIENTE i ON l.id_ingredient = i.id_ingredient
WHERE l.data_receptiei BETWEEN '2026-11-01' AND '2026-11-30';


-- 2. Gestiunea rețetelor

-- 2.1. Descompunere Rețetă – Ingrediente și cantități necesare
SELECT r.denumire AS reteta, i.nume AS ingredient, ri.cantitate AS cantitate_per_portie, i.unitate_masura
FROM RETETE r
JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
WHERE r.id_reteta = 1;

-- 2.2. Rețete generate de AI (stadiu de verificare/ciornă)
SELECT g.id_generare, r.denumire AS reteta_propusa, u.nume AS cofetar_solicitant, g.ingrediente_trimise, r.stare
FROM GENERARI_AI g
JOIN RETETE r ON g.id_reteta = r.id_reteta
JOIN UTILIZATORI u ON g.id_utilizator = u.id_utilizator
WHERE r.stare IN ('ciorna', 'verificata');

-- 2.3. Număr de rețete create per utilizator/cofetar
SELECT u.nume AS utilizator, COUNT(r.id_reteta) AS total_retete
FROM UTILIZATORI u
LEFT JOIN RETETE r ON u.id_utilizator = r.id_utilizator
GROUP BY u.id_utilizator, u.nume;

-- 2.4. Căutare rețete care conțin un ingredient specific
SELECT DISTINCT r.denumire AS reteta, r.sursa, r.stare
FROM RETETE r
JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
JOIN INGREDIENTE i ON ri.id_ingredient = i.id_ingredient
WHERE i.nume LIKE '%Ciocolată%';

-- 2.5. Rețete aprobate și numărul de ingrediente din compoziție
SELECT r.denumire AS reteta, COUNT(ri.id_ingredient) AS numar_ingrediente
FROM RETETE r
JOIN RETETE_INGREDIENTE ri ON r.id_reteta = ri.id_reteta
WHERE r.stare = 'aprobata'
GROUP BY r.id_reteta, r.denumire;


-- 3. Gestiunea producției

-- 3.1. Tabloul de Producție al zilei curente
SELECT p.id_sarcina, p.stare AS stare_productie, prod.denumire AS produs, cd.cantitate, c.id_comanda, cl.nume AS client
FROM PRODUCTIE p
JOIN COMENZI_DETALII cd ON p.id_detaliu = cd.id_detaliu
JOIN PRODUSE prod ON cd.id_produs = prod.id_produs
JOIN COMENZI c ON p.id_comanda = c.id_comanda
JOIN CLIENTI cl ON c.id_client = cl.id_client
WHERE p.data_productie = CURDATE();

-- 3.2. Încărcare Cofetari – Sarcini active în lucru per cofetar
SELECT u.nume AS cofetar, COUNT(p.id_sarcina) AS sarcini_in_lucru
FROM UTILIZATORI u
JOIN PRODUCTIE p ON u.id_utilizator = p.id_utilizator
WHERE p.stare != 'gata' AND u.rol = 'cofetar'
GROUP BY u.id_utilizator, u.nume;

-- 3.3. Comenzi personalizate (Custom) aflate în producție
SELECT c.id_comanda, cl.nume AS client, c.text_personalizat, c.model_dorit, c.data_livrare
FROM COMENZI c
JOIN CLIENTI cl ON c.id_client = cl.id_client
WHERE c.tip = 'custom' AND c.stare != 'finalizata';

-- 3.4. Detalii comanda pentru producție (Produse și cantități)
SELECT c.id_comanda, p.denumire AS produs, cd.cantitate
FROM COMENZI c
JOIN COMENZI_DETALII cd ON c.id_comanda = cd.id_comanda
JOIN PRODUSE p ON cd.id_produs = p.id_produs
WHERE c.id_comanda = 1;

-- 3.5. Stadiul sarcinilor de producție per comandă
SELECT c.id_comanda, p.stare AS stare_sarcina, p.data_productie, u.nume AS cofetar_alocat
FROM PRODUCTIE p
JOIN COMENZI c ON p.id_comanda = c.id_comanda
JOIN UTILIZATORI u ON p.id_utilizator = u.id_utilizator;


-- 4.Gestiunea vânzărilor

-- 4.1. Top cele mai vândute produse după bucăți și încasări
SELECT p.denumire AS produs, SUM(cd.cantitate) AS bucati_vandute, SUM(cd.cantitate * p.pret_vanzare) AS total_incasat
FROM COMENZI_DETALII cd
JOIN PRODUSE p ON cd.id_produs = p.id_produs
JOIN COMENZI c ON cd.id_comanda = c.id_comanda
WHERE c.stare = 'finalizata'
GROUP BY p.id_produs, p.denumire
ORDER BY bucati_vandute DESC;

-- 4.2. Valoarea totală per comandă
SELECT c.id_comanda, cl.nume AS client, SUM(cd.cantitate * p.pret_vanzare) AS valoare_totala
FROM COMENZI c
JOIN CLIENTI cl ON c.id_client = cl.id_client
JOIN COMENZI_DETALII cd ON c.id_comanda = cd.id_comanda
JOIN PRODUSE p ON cd.id_produs = p.id_produs
GROUP BY c.id_comanda, cl.nume;

-- 4.3. Clienți fideli (Vânzări totale peste un prag dat - HAVING)
SELECT cl.nume AS client, cl.telefon, COUNT(c.id_comanda) AS numar_comenzi, SUM(cd.cantitate * p.pret_vanzare) AS total_cheltuit
FROM CLIENTI cl
JOIN COMENZI c ON cl.id_client = c.id_client
JOIN COMENZI_DETALII cd ON c.id_comanda = cd.id_comanda
JOIN PRODUSE p ON cd.id_produs = p.id_produs
GROUP BY cl.id_client, cl.nume, cl.telefon
HAVING total_cheltuit > 200;

-- 4.4. Produse cu preț peste prețul mediu (Subinterogare)
SELECT id_produs, denumire, pret_vanzare
FROM PRODUSE
WHERE pret_vanzare > (SELECT AVG(pret_vanzare) FROM PRODUSE);

-- 4.5. Venituri totale în luna curentă
SELECT SUM(cd.cantitate * p.pret_vanzare) AS venit_lunar
FROM COMENZI_DETALII cd
JOIN PRODUSE p ON cd.id_produs = p.id_produs
JOIN COMENZI c ON cd.id_comanda = c.id_comanda
WHERE c.stare = 'finalizata'
  AND MONTH(c.data_livrare) = MONTH(CURDATE())
  AND YEAR(c.data_livrare) = YEAR(CURDATE());