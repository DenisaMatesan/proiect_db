USE laborator_cofetarie;

DELIMITER $$

-- 1. Trigger la introducerea unui lot nou: creste stocul ingredientului
DROP TRIGGER IF EXISTS trg_after_insert_lot$$
CREATE TRIGGER trg_after_insert_lot
AFTER INSERT ON LOTURI
FOR EACH ROW
BEGIN
    UPDATE INGREDIENTE
    SET stoc_curent = stoc_curent + NEW.cantitate_ramasa
    WHERE id_ingredient = NEW.id_ingredient;
END$$

-- 2. Trigger la actualizarea unui lot (ex: consum FEFO): ajusteaza stocul ingredientului
DROP TRIGGER IF EXISTS trg_after_update_lot$$
CREATE TRIGGER trg_after_update_lot
AFTER UPDATE ON LOTURI
FOR EACH ROW
BEGIN
    UPDATE INGREDIENTE
    SET stoc_curent = stoc_curent + (NEW.cantitate_ramasa - OLD.cantitate_ramasa)
    WHERE id_ingredient = NEW.id_ingredient;
END$$

-- 3. Trigger la stergerea unui lot: scade stocul ingredientului
DROP TRIGGER IF EXISTS trg_after_delete_lot$$
CREATE TRIGGER trg_after_delete_lot
AFTER DELETE ON LOTURI
FOR EACH ROW
BEGIN
    UPDATE INGREDIENTE
    SET stoc_curent = stoc_curent - OLD.cantitate_ramasa
    WHERE id_ingredient = OLD.id_ingredient;
END$$

-- 4. Trigger pentru prevenirea stocului negativ la nivelul ingredientelor
DROP TRIGGER IF EXISTS trg_check_stoc_negativ_ingrediente$$
CREATE TRIGGER trg_check_stoc_negativ_ingrediente
BEFORE UPDATE ON INGREDIENTE
FOR EACH ROW
BEGIN
    IF NEW.stoc_curent < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Eroare tranzacțională: Stocul curent al ingredientului nu poate fi negativ!';
    END IF;
END$$

-- 5. Trigger pentru prevenirea cantitatii negative in loturi
DROP TRIGGER IF EXISTS trg_check_stoc_negativ_loturi$$
CREATE TRIGGER trg_check_stoc_negativ_loturi
BEFORE UPDATE ON LOTURI
FOR EACH ROW
BEGIN
    IF NEW.cantitate_ramasa < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Eroare tranzacțională: Cantitatea rămasă din lot nu poate deveni negativă!';
    END IF;
END$$

DELIMITER ;
