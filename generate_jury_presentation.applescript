set outputDir to "/Users/nalrimet/Desktop/kmg-hr/hr-ai-app/presentation"
set deckName to "KMG_HR_AI_Command_Center_Jury_Presentation"
set keynotePath to outputDir & "/" & deckName & ".key"
set pdfPath to outputDir & "/" & deckName & ".pdf"
set pptxPath to outputDir & "/" & deckName & ".pptx"

do shell script "mkdir -p " & quoted form of outputDir
do shell script "rm -f " & quoted form of pdfPath
do shell script "rm -f " & quoted form of pptxPath
do shell script "rm -rf " & quoted form of keynotePath

on add_bullet_slide(docRef, masterName, slideTitle, bulletLines)
	tell application "Keynote"
		tell docRef
			set slideRef to make new slide with properties {base slide:(master slide masterName of docRef)}
			tell slideRef
				set object text of default title item to slideTitle
				set object text of default body item to bulletLines
			end tell
		end tell
	end tell
end add_bullet_slide

tell application "Keynote"
	activate
	set docRef to make new document with properties {document theme:theme "Техническая"}
	tell docRef
		set width to 1920
		set height to 1080
		delete slide 1
	end tell
	
	set titleSlide to make new slide at end of docRef with properties {base slide:(master slide "Заголовок и пункты" of docRef)}
	tell titleSlide
		set object text of default title item to "KMG HR AI Command Center"
		set object text of default body item to "AI-слой над Performance Management для оценки качества целей, стратегической связки и генерации сильных формулировок." & return & return & "Demo Day · 30 марта 2026"
	end tell
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "1. Проблема бизнеса", "SMART не гарантирует связь цели с бизнесом." & return & "Цели часто не связаны с KPI, ВНД и каскадом руководителя." & return & "Performance Management превращается в формальность." & return & "Руководитель не видит качество goal set по подразделению.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "2. Что делает решение", "Собирает единый контекст: сотрудник, проекты, KPI, каскад от руководителя и ВНД." & return & "Оценивает цель: SMART, стратегическая связка, риск дублирования, тип цели." & return & "Генерирует 3-5 сильных целей по контексту роли и фокусу квартала." & return & "Показывает зрелость целеполагания по подразделениям.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "3. Масштаб демо-данных", "450 сотрудников" & return & "9000 целей" & return & "160 ВНД" & return & "Полный workflow: от employee-level до department-level radar.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "4. Как проходит демо за 90 секунд", "1. Показываем radar зрелости по подразделениям." & return & "2. Открываем контекст сотрудника: роль, KPI, каскад, ВНД." & return & "3. Проверяем слабую цель и видим разбор + подтверждение из ВНД." & return & "4. Генерируем новый набор целей и возвращаем лучшую формулировку в Goal Studio.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "5. Почему это не просто LLM demo", "Hybrid architecture: retrieval + deterministic scoring + optional external LLM." & return & "Каждый вывод объясним и привязан к ВНД, KPI и контексту роли." & return & "Система остаётся рабочей даже без внешнего LLM-ключа." & return & "Готова к интеграции через API в HR/PM-платформу.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "6. Эффект для бизнеса", "Снижается доля формальных целей-активностей." & return & "Растет стратегическая связка целей с задачами компании." & return & "Сотрудник получает понятную и измеримую формулировку цели." & return & "Руководитель и HR получают прозрачность качества goal set.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "7. Внедрение после хакатона", "Подключение к боевой HR-системе вместо CSV." & return & "Историческая калибровка достижимости по фактическим результатам." & return & "Feedback loop от руководителей и HR BP." & return & "Расширение до полного performance cycle.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "8. Q&A", "GitHub: github.com/temirrrr/hr-ai-app" & return & "Формат финала: live demo на собственном ноутбуке" & return & "Ключевой тезис: это не SMART-checker, а AI-слой над Performance Management.")
	
	save docRef in POSIX file keynotePath
	export docRef to POSIX file pptxPath as Microsoft PowerPoint
	export docRef to POSIX file pdfPath as PDF
	close docRef saving yes
end tell
