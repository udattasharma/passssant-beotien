import bpy
import bgl
import blf

from mathutils import Vector
from mathutils.geometry import intersect_line_line_2d
from math import fmod


#hardcode some button data...easily generated form bezier button data script

button_data = button_data = [

    [(0.4040972688108701,0.9034840042370106),
    (0.43104241946701966,0.9062432167853265),
    (0.45516192854658594,0.9018705153766557),
    (0.47814679724621223,0.8905493942671182),
    (0.4863345644893785,0.8793075914002878),
    (0.48660594619121234,0.8650759865224141),
    (0.4814562092834496,0.8521336571878297),
    (0.4653949379239144,0.8245019434031761),
    (0.4499427173565949,0.7993982153253751),
    (0.43378722017391513,0.7855396894676634),
    (0.41455707878843934,0.7852296401225098),
    (0.3985189655229802,0.7945247466897558),
    (0.3847733619313369,0.8088269589676107),
    (0.3735967487452314,0.818663270901614),
    (0.3615951196051821,0.8275432314521194),
    (0.3517696431096915,0.8392046419868426),
    (0.3480389591378617,0.8496054590213984),
    (0.34856855004765114,0.8597962243524994),
    (0.35433746498754665,0.8689430341338267),
    (0.3843852691009482,0.8956237788443091)],

    [(0.27154182553626743,0.852978892211678),
    (0.28739561241225686,0.8600010353863468),
    (0.30274091269660564,0.8620540322951307),
    (0.3223376176751639,0.8589926314060723),
    (0.33195353820621654,0.8520156004819432),
    (0.33602854833522694,0.8402584414970949),
    (0.33689201947291186,0.8278814671013778),
    (0.33620365043798894,0.8039492411404179),
    (0.3325193180642411,0.7854645495966702),
    (0.3236508657409142,0.7729588955161326),
    (0.3096714149730038,0.7660723015526617),
    (0.29672774006108776,0.7672001078161542),
    (0.28271780134363683,0.7740932880265642),
    (0.2710242385926734,0.7795863596134737),
    (0.2593519572095077,0.7844782414125786),
    (0.24819843129761882,0.7918847239650793),
    (0.241943515071493,0.7994898562236457),
    (0.23923173412411733,0.8081490712719027),
    (0.24111970305516164,0.8174488519498796),
    (0.25832294465010136,0.8437725229284606)],

    [(0.13762478193679992,0.7850724200342867),
    (0.15071172542460579,0.7947946411745388),
    (0.1654776307329296,0.7988958900615162),
    (0.18248875575384801,0.8003648355885091),
    (0.1995589976525341,0.8008505181853713),
    (0.21467174322305288,0.7988590637345451),
    (0.22861355323560711,0.7905472200974297),
    (0.23920901865416347,0.77518837551494),
    (0.2428245318293839,0.7578877212031756),
    (0.24394268888701137,0.7380408804806515),
    (0.24689100816531734,0.718817608621553),
    (0.24518451512439543,0.7011379972412831),
    (0.23562634818881395,0.6851963052146149),
    (0.21986445008060362,0.6746348687385771),
    (0.20280584034385024,0.6730058703289787),
    (0.18323386920124335,0.6773677362991368),
    (0.16822699932076673,0.679438721452249),
    (0.1547481741400858,0.683413202790614),
    (0.14350146699798086,0.6921870751914987),
    (0.132978503410649,0.7102016645074871),
    (0.12903112837353056,0.7290364894368992),
    (0.12848277020095772,0.7505972415806341),
    (0.13107590132612312,0.7746679203670338)],

    [(0.07298322479363624,0.645662110093296),
    (0.08094061945989517,0.656722260020355),
    (0.09008654399297807,0.6650342452971895),
    (0.10163616537938588,0.6728261295254155),
    (0.10980096928308986,0.6779127659383104),
    (0.11766723206881877,0.6814323713187217),
    (0.1270873179832232,0.6826254734927285),
    (0.1405177377898949,0.6800069800053582),
    (0.15176501149087632,0.6741217080362056),
    (0.16409455428565317,0.6669582084218552),
    (0.17682461879617145,0.6604761374961907),
    (0.18783142366401698,0.6541340774328764),
    (0.1991837940365854,0.6456751409474549),
    (0.20908412712363086,0.6381532928437311),
    (0.21715479372901475,0.6306599851434098),
    (0.2212414006100281,0.6203360784763362),
    (0.2195060484763355,0.605864606734133),
    (0.21191106116265104,0.5942606311055129),
    (0.20021282430095663,0.5840029764170576),
    (0.18542471696666077,0.575596375807851),
    (0.1700917393378754,0.5719360867764237),
    (0.15235766748560392,0.5705565867320551),
    (0.13285675521958298,0.5695879835128534),
    (0.11548702498730022,0.5713409166766817),
    (0.09854717130254648,0.5793638506967222),
    (0.08291426271604217,0.5945975919972992),
    (0.07421261329318508,0.6124629638691949),
    (0.06996197433870717,0.6338666375644257),
    (0.07099713052093035,0.6418397498132657)],

    [(0.04912904231791134,0.5361680209666443),
    (0.06267536325099415,0.5501868121665402),
    (0.07910193229862213,0.5582466079234817),
    (0.09926129220890187,0.561783280890047),
    (0.11382943305940448,0.5606215519138252),
    (0.12640110010153444,0.5557312635615604),
    (0.13990769551964533,0.548906070416328),
    (0.15886222371667863,0.5403350260932231),
    (0.1748484083201154,0.5311601362375802),
    (0.18793264294829307,0.5166508112804422),
    (0.19244351390296532,0.506434657029689),
    (0.19332249458989387,0.49637115498621737),
    (0.19148098348672088,0.485331967737588),
    (0.1885745895652744,0.47655628943028466),
    (0.18402965425815382,0.46951389177578173),
    (0.17689255274645435,0.4634972843770752),
    (0.15829591270970733,0.4546789016944572),
    (0.13942067619793386,0.4516727757057854),
    (0.11790129170466447,0.4517843878044519),
    (0.09869681366579669,0.45289633041940297),
    (0.08192945945396614,0.45663115735301707),
    (0.06566685165994314,0.46565307631201047),
    (0.05521957237127481,0.47584231901613083),
    (0.04893540754315072,0.4873568137521969),
    (0.04505385956549325,0.5012751823912368),
    (0.043879427276962944,0.5251069857913407)],

    [(0.024027850476330832,0.3681507015450698),
    (0.020665801578475522,0.3907132006022804),
    (0.022915407696121614,0.4130613987644626),
    (0.03460759831230609,0.43410895479589606),
    (0.04433578602572616,0.4412278378987238),
    (0.05563916233420274,0.4440250453016937),
    (0.06871099463447498,0.44525663806937127),
    (0.08372798290238623,0.44549820461033035),
    (0.09707294969601638,0.4434847251831809),
    (0.1118119611626723,0.4400468459207017),
    (0.13109570432935258,0.4358798407941229),
    (0.14787080446332249,0.4308877843036704),
    (0.16426802753164532,0.42133248557240116),
    (0.17518414756932432,0.4114483702331949),
    (0.18251736697711024,0.4006237671590323),
    (0.18693820818531687,0.3871019189136687),
    (0.1899168383635145,0.3708528332865804),
    (0.1879610771219064,0.3565357488382179),
    (0.17724024284696402,0.3351636962102806),
    (0.17682978864591933,0.3224652704720207),
    (0.17641936985480441,0.30976684473376087),
    (0.17119507733988992,0.29737967227826706),
    (0.1609132553743598,0.28772534967836805),
    (0.14871352538215635,0.2823802207780794),
    (0.1340412793381006,0.2793167838180587),
    (0.11156453427833465,0.27757488084735676),
    (0.09143532592326258,0.2803478147434625),
    (0.07012416066958194,0.2876079480561825),
    (0.05183295340839341,0.29600072108781),
    (0.03734896425601294,0.3063645524507106),
    (0.026043388105648782,0.32166096932699817),
    (0.020461388906338116,0.3519082021649206)],

    [(0.023295387226349405,0.21383693642352486),
    (0.021728710293163766,0.23125724088801589),
    (0.022106932605626226,0.24678677903700996),
    (0.03011004149123112,0.26071853262950667),
    (0.050820335646475194,0.2722992262292964),
    (0.07421690232092969,0.2737802465423443),
    (0.10047801280607192,0.2715158877627036),
    (0.11797685649481496,0.26952646938283964),
    (0.13305962755977496,0.2652307314565457),
    (0.14803200816864587,0.2568871251124177),
    (0.1616382382766752,0.24593000037605345),
    (0.17112466469452242,0.23369101847668888),
    (0.17691994232713917,0.2180164235503511),
    (0.1787277608821265,0.20373487296652282),
    (0.17648000935955263,0.19089505537865148),
    (0.16892021951606948,0.17914572198828455),
    (0.1655078708129617,0.16684450713733168),
    (0.1610975817638295,0.15898739781845087),
    (0.1532901879863598,0.15246449924375013),
    (0.13509187424970784,0.14392890026035504),
    (0.116487081076629,0.14163839124757185),
    (0.09558930019568235,0.14320074816932432),
    (0.07125355595367333,0.1470619354373583),
    (0.05071572143518145,0.15467078573855164),
    (0.03292468385837643,0.1695325103168601),
    (0.02345569683094584,0.19756853467974161)],

    [(0.03633534616357843,0.07899192249927817),
    (0.03405785915247183,0.0959636451208339),
    (0.03289527591169415,0.11116637617540606),
    (0.03975668898885033,0.12483114774984413),
    (0.059050462018140785,0.13516634133203514),
    (0.08105718009624843,0.13537676483975272),
    (0.10555802756209785,0.13203445697774974),
    (0.12408082019028871,0.129398488690033),
    (0.13995521564541005,0.12446112283612575),
    (0.15499607905847546,0.11468105957557799),
    (0.16609700351967618,0.10318011799013521),
    (0.17275750508150198,0.09059736763998412),
    (0.1751890872545286,0.07539026345908414),
    (0.17355344948309645,0.06375966841575195),
    (0.16854510442494522,0.05403246332788327),
    (0.16091472488644565,0.04428507458004),
    (0.15460954426499715,0.038015148969928685),
    (0.14786386411708563,0.03351228065938672),
    (0.13974226032771322,0.029276593547758398),
    (0.12579474931646442,0.02211491311855039),
    (0.11273490327742271,0.017029020314180975),
    (0.09740070400605991,0.01523950426664867),
    (0.07597234958977242,0.016823359442018824),
    (0.057692469079872265,0.022663660800350812),
    (0.042193772979716555,0.035444653642375146),
    (0.035588479924659,0.06309044730035758)],

    [(0.5939009724487375,0.907512804407658),
    (0.566955821792588,0.910272016955974),
    (0.5428363127130217,0.9058993155473033),
    (0.5198514794233252,0.8945781944377658),
    (0.5116636767702292,0.8833363915709354),
    (0.5113922950683953,0.8691047866930617),
    (0.5165420673860879,0.8561624573584773),
    (0.5326033033356933,0.8285307435738236),
    (0.5480555239030127,0.8034270154960226),
    (0.5642110564956223,0.7895684896383109),
    (0.5834411624711683,0.7892584402931574),
    (0.5994792757366274,0.7985535468604034),
    (0.613224843918341,0.8128557591382582),
    (0.6244014925143763,0.8226920710722615),
    (0.6364031216544256,0.8315720316227669),
    (0.6462285981499162,0.8432334421574902),
    (0.6499593175316758,0.8536342591920459),
    (0.6494297266218862,0.8638250245231468),
    (0.6436607408621312,0.8729718343044742),
    (0.6136129367487296,0.8996525790149567)],

    [(0.7252570459917623,0.8561212402002134),
    (0.709403241410808,0.8631433833748822),
    (0.6940579234214943,0.8651963802836661),
    (0.6744612184429362,0.8621349793946077),
    (0.664845368731743,0.8551579484704787),
    (0.6607703231928028,0.8434007894856304),
    (0.6599068166451881,0.8310238150899132),
    (0.6605951856801111,0.8070915891289533),
    (0.6642795180538589,0.7886068975852056),
    (0.6731480057871156,0.776101243504668),
    (0.6871274211450962,0.769214649541197),
    (0.7000710960570122,0.7703424558046895),
    (0.7140810347744632,0.7772356360150996),
    (0.7257745975254266,0.7827287076020091),
    (0.737446914318522,0.7876206602209735),
    (0.7486004048204812,0.7950270719536147),
    (0.7548553564565368,0.8026322042121811),
    (0.7575671196989476,0.8112914192604381),
    (0.7556791330629383,0.820591199938415),
    (0.7384759268779284,0.846914870916996)],

    [(0.849741858070911,0.779774457160465),
    (0.837190383541238,0.7901024005595335),
    (0.8226616893525103,0.7948960552134288),
    (0.8057499068895896,0.7971668940102191),
    (0.788726583147862,0.7984585774287334),
    (0.7735260209514888,0.7971837491367945),
    (0.7591572380056476,0.7895415780916781),
    (0.7477542491384587,0.7747033302968138),
    (0.7432189453322382,0.7575960850215077),
    (0.7410418720295052,0.7378279251629547),
    (0.737070152665663,0.7187690261978948),
    (0.7378300497587416,0.7010317674519432),
    (0.7465248163764976,0.6846592073997122),
    (0.7617031411369689,0.6733667683332963),
    (0.778653803702788,0.6709338228779732),
    (0.7984347111360617,0.6743652575332324),
    (0.8135338592935449,0.6757244322779073),
    (0.8272083951561199,0.6790567899496421),
    (0.8389101021909328,0.6872878281269995),
    (0.8503824945204904,0.7047817498355031),
    (0.855331244666822,0.7234055315834265),
    (0.8570308504764016,0.7449122481743171),
    (0.8557268444023239,0.7690740721199705)],

    [(0.9250149412198706,0.645662110093296),
    (0.917057550979853,0.656722260020355),
    (0.9079115910368403,0.6650342452971895),
    (0.8963620050603622,0.6728261295254155),
    (0.8881971834516934,0.6779127659383104),
    (0.8803309383709294,0.6814323713187217),
    (0.8709108347515601,0.6826254734927285),
    (0.8574804149448884,0.6800069800053582),
    (0.8462331589488717,0.6741217080362056),
    (0.8339036338590599,0.6669582084218552),
    (0.8211735516435766,0.6604761374961907),
    (0.8101667290707663,0.6541340774328764),
    (0.7988143764031627,0.6456751409474549),
    (0.7889140433161173,0.6381532928437311),
    (0.7808434121206631,0.6306599851434098),
    (0.7767567521247551,0.6203360784763362),
    (0.7784921219634126,0.605864606734133),
    (0.786087126982062,0.5942606311055129),
    (0.7977853638437563,0.5840029764170576),
    (0.8125734711780522,0.575596375807851),
    (0.8279064665118024,0.5719360867764237),
    (0.8456404675442144,0.5705565867320551),
    (0.8651414240726476,0.5695879835128534),
    (0.882511127747483,0.5713409166766817),
    (0.899451025694649,0.5793638506967222),
    (0.9150839431336357,0.5945975919972992),
    (0.9237855792777692,0.6124629638691949),
    (0.9280361872485585,0.6338666375644257),
    (0.9270010133613704,0.6418397498132657)],

    [(0.9506542090756641,0.5361680209666443),
    (0.9371079279787523,0.5501868121665402),
    (0.920681332373677,0.5582466079234817),
    (0.9005219636109149,0.561783280890047),
    (0.8859538227604122,0.5606215519138252),
    (0.8733821645707647,0.5557312635615604),
    (0.8598755425952065,0.548906070416328),
    (0.8409210321031381,0.5403350260932231),
    (0.8249348652046662,0.5311601362375802),
    (0.8118506128715236,0.5166508112804422),
    (0.8073397419168513,0.506434657029689),
    (0.8064607258199931,0.49637115498621737),
    (0.8083022546281309,0.485331967737588),
    (0.8112086308446125,0.47655628943028466),
    (0.8157535661517331,0.46951389177578173),
    (0.8228907207783273,0.4634972843770752),
    (0.8414873785200391,0.4546789016944572),
    (0.8603625707694004,0.4516727757057854),
    (0.8818819641151522,0.4517843878044519),
    (0.9010864687114674,0.45289633041940297),
    (0.9178537786608857,0.45663115735301707),
    (0.9341164262910796,0.46565307631201047),
    (0.9445637011535067,0.47584231901613083),
    (0.9508478305717011,0.4873568137521969),
    (0.9547293962543234,0.5012751823912368),
    (0.9559038019854064,0.5251069857913407)],

    [(0.9689127728078367,0.3703889986163924),
    (0.9722748040007272,0.392951497673603),
    (0.9700252111618047,0.4152996958357852),
    (0.9583330648080325,0.4363472518672187),
    (0.9486048239797177,0.44346617037997615),
    (0.9373014786549297,0.44626334237301624),
    (0.9242296197972102,0.4474949351406939),
    (0.909212693496676,0.44773650168165297),
    (0.8958676824406336,0.4457230222545035),
    (0.8811286532690128,0.4422851429920243),
    (0.8618449012498501,0.4381181378654455),
    (0.8450698719357397,0.43312611678492285),
    (0.8286725957525223,0.42357081805365354),
    (0.8177564934198082,0.41368666730451753),
    (0.8104232386020924,0.4028620642303549),
    (0.8060024505087805,0.3893402159849913),
    (0.8030238380355477,0.37309113035790303),
    (0.8049795284572963,0.3587740459095405),
    (0.8157003804372035,0.33740202869153296),
    (0.8161108523432131,0.32470356754334334),
    (0.8165212534293631,0.3120051418050835),
    (0.8217455636492426,0.2996179693495897),
    (0.8320274033197376,0.28996364674969066),
    (0.844227115606976,0.284618517849402),
    (0.8588993616510319,0.2815550808893813),
    (0.8813760978583154,0.2798131779186794),
    (0.901505297360905,0.2825861118147851),
    (0.9228164803195505,0.2898462451275051),
    (0.9411076920069803,0.29823900045416774),
    (0.9555916988643256,0.3086028495220332),
    (0.96689723960476,0.3238992663983208),
    (0.9724792609352768,0.3541464992362432)],

    [(0.9693478900249731,0.21414601199560945),
    (0.9709145669581588,0.23156631646010048),
    (0.970536318088249,0.24709587231405944),
    (0.9625332490388151,0.26102760820159127),
    (0.9418229017686763,0.272608301801381),
    (0.918426357225428,0.2740893221144289),
    (0.8921652201828384,0.2718249633347882),
    (0.8746664119040252,0.26983554495492423),
    (0.8595836231341003,0.2655398070286303),
    (0.8446112425252293,0.2571962006845023),
    (0.8310050478271298,0.24623909365310293),
    (0.8215185859993528,0.23400009404877348),
    (0.815723326071701,0.2183254991224357),
    (0.8139155075167136,0.2040439485386074),
    (0.8161632590392875,0.19120413095073607),
    (0.8237230665877355,0.17945479756036914),
    (0.8271353798809136,0.16715358270941627),
    (0.8315456866350106,0.15929645568557058),
    (0.8393530804124804,0.15277357481583473),
    (0.8575513764441675,0.14423797583243964),
    (0.8761561784697287,0.14194746681965645),
    (0.8970539859081227,0.14350982374140892),
    (0.9213897434288554,0.14737101100944291),
    (0.941927573521106,0.15497987901560112),
    (0.9597185845404637,0.16984160359390957),
    (0.9691875538629294,0.1978776102518262)],

    [(0.9616628729648231,0.07762226641538836),
    (0.9639403688284122,0.0945939890369441),
    (0.9651029476429486,0.10979672009151625),
    (0.9582414947296214,0.12346149166595434),
    (0.9389477571102608,0.13379668524814534),
    (0.9169410523108767,0.1340071087558629),
    (0.8924401428776503,0.13066480089385993),
    (0.8739173502494594,0.1280288326061432),
    (0.8580430079092327,0.12309146675223594),
    (0.8430021444961673,0.1133114034916882),
    (0.8319012023300016,0.1018104619062454),
    (0.8252406653582461,0.08922771155609432),
    (0.8228091363001141,0.07402061180143556),
    (0.8244447917765112,0.062390012331862144),
    (0.8294531014247326,0.05266280724399346),
    (0.837083516373162,0.042915418496150194),
    (0.8433886792896457,0.036645492886038876),
    (0.8501343417325923,0.03214262457549691),
    (0.8582559632269295,0.027906937463868593),
    (0.8722034388282486,0.020745257034660583),
    (0.8852633291297025,0.01565936423029117),
    (0.9005975284010653,0.013869848182758862),
    (0.922025847407423,0.015453703358129019),
    (0.9403057279173231,0.021294004716461007),
    (0.9558044417224437,0.034074997558485344),
    (0.9624097392037425,0.06172079121646777)]]
    

button_names = [
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    21,
    22,
    23,
    24,
    25,
    26,
    27,
    28]

# slightly ugly use of the string representation of GL_LINE_TYPE.
#modified form zeffi's edge filet script
#not very efficient scaling and translating every time
def draw_polyline_2d_loop(context, points, scale, offset, color, LINE_TYPE):
    region = context.region
    rv3d = context.space_data.region_3d

    bgl.glColor4f(*color)  #black or white?

    if LINE_TYPE == "GL_LINE_STIPPLE":
        bgl.glLineStipple(4, 0x5555)
        bgl.glEnable(bgl.GL_LINE_STIPPLE)
        bgl.glColor4f(0.3, 0.3, 0.3, 1.0) #boring grey
    
    bgl.glBegin(bgl.GL_LINE_STRIP)
    for coord in points:
        bgl.glVertex2f(scale*coord[0]+offset[0], scale*coord[1] + offset[1])
    bgl.glVertex2f(scale*points[0][0]+offset[0], scale*points[0][1] + offset[1])
    bgl.glEnd()
    
    if LINE_TYPE == "GL_LINE_STIPPLE":
        bgl.glDisable(bgl.GL_LINE_STIPPLE)
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines    
    return


def outside_loop(loop, scale, offset):    
    xs = [scale*v[0] + offset[0] for v in loop]
    ys = [scale*v[1] + offset[1]  for v in loop]
    
    maxx = max(xs)
    maxy = max(ys)
    
    bound = (1.1*maxx, 1.1*maxy)
    return bound

def point_inside_loop(loop, point, scale, offset):
        
    nverts = len(loop)
    
    #vectorize our two item tuple
    out = Vector(outside_loop(loop, scale, offset))
    pt = Vector(point)
    
    intersections = 0
    for i in range(0,nverts):
        a = scale*Vector(loop[i-1]) + Vector(offset)
        b = scale*Vector(loop[i]) + Vector(offset)
        if intersect_line_line_2d(pt,out,a,b):
            intersections += 1
    
    inside = False
    if fmod(intersections,2):
        inside = True
    
    return inside

def draw_callback_px(self, context):

    region = bpy.context.region
    rv3d = bpy.context.space_data.region_3d
    
    width = region.width
    height = region.height
    mid = (width/2,height/2)
    
    #need to check height available..whatev
    #menu_width is also our scale!
    menu_aspect = 1.06504085828804
    menu_width = .8*width
    menu_height = menu_width/menu_aspect
    if menu_height > height:
        menu_width = menu_aspect*.8*height
    
    #origin of menu is bottom left corner
    menu_loc = (.1 * width, .1*height) #for now
    
    #draw all the buttons
    color = (1.0,1.0,1.0,1.0)
    for button in button_data: #each of those is a loop
        
        select = point_inside_loop(button,self.mouse,menu_width, menu_loc)
        
        if select:
            color = (1.0,0.1,0.1,0.5)
        
        draw_polyline_2d_loop(context, button, menu_width, menu_loc, color,"GL_BLEND")
        color = (1.0,1.0,1.0,1.0)
    

class ModalDrawOperator(bpy.types.Operator):
    '''Draw a line with the mouse'''
    bl_idname = "view3d.modal_operator"
    bl_label = "Simple Modal View3D Operator"

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.mouse = (event.mouse_region_x, event.mouse_region_y)

        elif event.type == 'LEFTMOUSE':
            context.region.callback_remove(self._handle)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            context.region.callback_remove(self._handle)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)

            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = context.region.callback_add(draw_callback_px, (self, context), 'POST_PIXEL')

            self.mouse = (0,0)

            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(ModalDrawOperator)


def unregister():
    bpy.utils.unregister_class(ModalDrawOperator)

if __name__ == "__main__":
    register()
