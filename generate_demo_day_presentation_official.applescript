set outputDir to "/Users/nalrimet/Desktop/kmg-hr/hr-ai-app/presentation"
set deckName to "KMG_HR_AI_Command_Center_Demo_Day_Official"
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
	set docRef to make new document with properties {document theme:theme "Официальная"}
	tell docRef
		set width to 1920
		set height to 1080
		delete slide 1
	end tell
	
	set titleSlide to make new slide at end of docRef with properties {base slide:(master slide "Заголовок и пункты" of docRef)}
	tell titleSlide
		set object text of default title item to "KMG HR AI Command Center"
		set object text of default body item to "AI-слой над Performance Management для качества целеполагания, стратегической связки и генерации сильных целей." & return & return & "Финал хакатона · Demo Day · 30 марта 2026"
	end tell
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "1. Проблема бизнеса", "SMART не гарантирует реальную полезность цели." & return & "Цели часто не связаны с KPI, ВНД и задачами руководителя." & return & "Руководители не видят зрелость goal set по подразделениям." & return & "Performance management становится формальностью вместо инструмента управления.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "2. Наше решение", "Employee workspace: роль, проекты, KPI, каскад от руководителя и health набора целей." & return & "Goal Studio: SMART, strategic alignment, duplicate risk и улучшенная формулировка." & return & "AI generation: 3-5 целей на основе ВНД, KPI и контекста сотрудника." & return & "Team radar: зрелость целеполагания по подразделениям и кластеры рисков.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "3. Как проходит демо", "1. Показываем dashboard зрелости целеполагания." & return & "2. Выбираем сотрудника и собираем контекст не в вакууме, а в контуре бизнеса." & return & "3. Проверяем слабую цель и видим SMART-разбор, связку с ВНД и риски." & return & "4. Генерируем новый набор целей и возвращаем лучшую формулировку обратно в Goal Studio.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "4. Почему решение конкурентное", "Это не просто SMART-checker, а AI command center для качества целеполагания." & return & "Hybrid architecture: retrieval + deterministic scoring + optional external LLM." & return & "Решение объяснимо: каждая цель подкрепляется ВНД, KPI и контекстом роли." & return & "Есть value и для сотрудника, и для руководителя, и для HR/exec уровня.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "5. Эффект для бизнеса", "Снижается доля формальных activity-based целей." & return & "Растет стратегическая связка целей с задачами компании и руководителя." & return & "Сотрудник получает понятную улучшенную формулировку, а не только абстрактный score." & return & "Систему можно встроить в любую HR/PM-платформу через API.")
	
	my add_bullet_slide(docRef, "Заголовок и пункты", "6. Внедрение", "Подключение к боевой HR-системе вместо CSV." & return & "Историческая калибровка достижимости по фактическим результатам." & return & "Feedback loop от руководителей и HR BP." & return & "Переход от работы с одной целью к управлению полным квартальным goal set.")
	
	save docRef in POSIX file keynotePath
	export docRef to POSIX file pptxPath as Microsoft PowerPoint
	export docRef to POSIX file pdfPath as PDF
	close docRef saving yes
end tell
